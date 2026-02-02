import json
import os
from pathlib import Path
from typing import Any, Callable, Generator, Optional
from uuid import uuid4
import warnings

import backoff
import mlflow
import openai
from databricks.sdk import WorkspaceClient
from databricks_openai import UCFunctionToolkit, VectorSearchRetrieverTool
from mlflow.entities import SpanType
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    Message,
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)
from openai import OpenAI
from pydantic import BaseModel
from unitycatalog.ai.core.base import get_uc_function_client

def get_dbutils():
    try:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        dbutils = DBUtils(spark)
        return dbutils
    except (ImportError, Exception):
        # Spark not available (e.g., MLflow validation environment)
        try:
            import IPython
            ipython = IPython.get_ipython()
            if ipython and "dbutils" in ipython.user_ns:
                return ipython.user_ns["dbutils"]
        except (ImportError, AttributeError, RuntimeError):
            pass
    return None  # dbutils not available
    
dbutils = get_dbutils()

# ============================================================================
# Load shared configuration from multiple sources (in priority order):
# 1. config/dc_assistant.json file
# 2. DC_ASSISTANT_CONFIG_JSON environment variable
# 3. Individual environment variables from app.yaml
# ============================================================================
def load_config() -> dict:
    """Load configuration from file, JSON env var, or individual env vars."""
    # Priority 1: Config file
    config_path = Path(__file__).parent / "config" / "dc_assistant.json"
    if config_path.exists():
        return json.loads(config_path.read_text())

    # Priority 2: JSON config env var
    config_env = os.getenv("DC_ASSISTANT_CONFIG_JSON")
    if config_env:
        return json.loads(config_env)

    # Priority 3: Build config from individual env vars (app.yaml style)
    prompt_name = os.getenv("PROMPT_NAME")
    llm_model = os.getenv("LLM_MODEL")
    uc_catalog = os.getenv("UC_CATALOG")
    uc_schema = os.getenv("UC_SCHEMA")

    if prompt_name and llm_model:
        # Build a minimal config from env vars
        return {
            "workspace": {
                "catalog": uc_catalog or "ac_demo",
                "schema": uc_schema or "dc_assistant"
            },
            "prompt_registry": {
                "prompt_name": prompt_name
            },
            "llm": {
                "endpoint_name": llm_model
            },
            "tools": {
                "uc_tool_names": []  # Will need to be set via DC_ASSISTANT_CONFIG_JSON for full functionality
            },
            "prompt_registry_auth": {
                "use_oauth": True,
                "secret_scope_name": os.getenv("SECRET_SCOPE_NAME", "dc-assistant-secrets"),
                "oauth_client_id_key": os.getenv("OAUTH_CLIENT_ID_KEY", "oauth-client-id"),
                "oauth_client_secret_key": os.getenv("OAUTH_CLIENT_SECRET_KEY", "oauth-client-secret"),
                "databricks_host": os.getenv("DATABRICKS_HOST", "")
            }
        }

    raise FileNotFoundError(
        "Configuration not found. Set one of: "
        "config/dc_assistant.json file, DC_ASSISTANT_CONFIG_JSON env var, "
        "or PROMPT_NAME + LLM_MODEL env vars"
    )

CONFIG = load_config()

PROMPT_NAME = CONFIG["prompt_registry"]["prompt_name"]
LLM_ENDPOINT_NAME = CONFIG["llm"]["endpoint_name"]
UC_TOOL_NAMES = CONFIG["tools"].get("uc_tool_names", [])
SECRET_SCOPE_NAME = CONFIG.get("prompt_registry_auth", {}).get("secret_scope_name", "dc-assistant-secrets")
CLIENT_ID_KEY = CONFIG.get("prompt_registry_auth", {}).get("oauth_client_id_key", "oauth-client-id")
CLIENT_SECRET_KEY = CONFIG.get("prompt_registry_auth", {}).get("oauth_client_secret_key", "oauth-client-secret")
DATABRICKS_HOST = CONFIG.get("prompt_registry_auth", {}).get("databricks_host", "")

############################################
# Configure authentication for Prompt Registry access
# Priority order:
# 1. Databricks Apps run_as service principal (automatic - no secrets needed)
# 2. Environment variables (DATABRICKS_CLIENT_ID/SECRET or DATABRICKS_TOKEN)
# 3. Workspace secrets (fallback for notebook runs)
# See: https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication
############################################

def setup_authentication():
    """Set up Databricks authentication based on available credentials."""
    # Set host if configured but not in environment
    if DATABRICKS_HOST and not os.getenv("DATABRICKS_HOST"):
        host = DATABRICKS_HOST.rstrip("/")
        os.environ["DATABRICKS_HOST"] = host

    # Check if we're running in Databricks Apps with run_as (service principal)
    # In this case, authentication is automatic - no secrets needed
    if os.getenv("DATABRICKS_RUNTIME_VERSION") or os.getenv("DB_IS_DRIVER"):
        # Running in Databricks - use default authentication
        return WorkspaceClient()

    # Check for existing OAuth credentials in environment
    if os.getenv("DATABRICKS_CLIENT_ID") and os.getenv("DATABRICKS_CLIENT_SECRET"):
        return WorkspaceClient(
            host=os.environ.get("DATABRICKS_HOST"),
            client_id=os.environ.get("DATABRICKS_CLIENT_ID"),
            client_secret=os.environ.get("DATABRICKS_CLIENT_SECRET"),
        )

    # Check for PAT token
    if os.getenv("DATABRICKS_TOKEN"):
        return WorkspaceClient(
            host=os.environ.get("DATABRICKS_HOST"),
            token=os.environ.get("DATABRICKS_TOKEN"),
        )

    # Try to load from workspace secrets (for notebook runs)
    if dbutils:
        try:
            client_id = dbutils.secrets.get(scope=SECRET_SCOPE_NAME, key=CLIENT_ID_KEY)
            client_secret = dbutils.secrets.get(scope=SECRET_SCOPE_NAME, key=CLIENT_SECRET_KEY)
            os.environ["DATABRICKS_CLIENT_ID"] = client_id.strip()
            os.environ["DATABRICKS_CLIENT_SECRET"] = client_secret.strip()
            return WorkspaceClient(
                host=os.environ.get("DATABRICKS_HOST"),
                client_id=client_id.strip(),
                client_secret=client_secret.strip(),
            )
        except Exception as e:
            print(f"Warning: Could not load secrets from scope '{SECRET_SCOPE_NAME}': {e}")

    # Fall back to default authentication (will use ~/.databrickscfg or environment)
    return WorkspaceClient()

WORKSPACE_CLIENT = setup_authentication()

# Configure MLflow to use Unity Catalog registry
# This ensures MLflow's internal client uses the correct registry and authentication
mlflow.set_registry_uri("databricks-uc")

############################################
# Define your LLM endpoint and system prompt
############################################
PROMPT_URI_AGENT = f"prompts:/{PROMPT_NAME}@production"
SYSTEM_PROMPT = mlflow.genai.load_prompt(PROMPT_URI_AGENT)

###############################################################################
## Define tools for your agent, enabling it to retrieve data or take actions
## beyond text generation
## To create and see usage examples of more tools, see
## https://docs.databricks.com/generative-ai/agent-framework/agent-tool.html
###############################################################################
class ToolInfo(BaseModel):
    """
    Class representing a tool for the agent.
    - "name" (str): The name of the tool.
    - "spec" (dict): JSON description of the tool (matches OpenAI Responses format)
    - "exec_fn" (Callable): Function that implements the tool logic
    """

    name: str
    spec: dict
    exec_fn: Callable


def create_tool_info(tool_spec, exec_fn_param: Optional[Callable] = None):
    tool_spec["function"].pop("strict", None)
    tool_name = tool_spec["function"]["name"]
    udf_name = tool_name.replace("__", ".")

    # Define a wrapper that accepts kwargs for the UC tool call,
    # then passes them to the UC tool execution client
    def exec_fn(**kwargs):
        function_result = uc_function_client.execute_function(udf_name, kwargs)
        if function_result.error is not None:
            return function_result.error
        else:
            return function_result.value
    return ToolInfo(name=tool_name, spec=tool_spec, exec_fn=exec_fn_param or exec_fn)


TOOL_INFOS = []

uc_toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)
uc_function_client = get_uc_function_client()
for tool_spec in uc_toolkit.tools:
    TOOL_INFOS.append(create_tool_info(tool_spec))


# Use Databricks vector search indexes as tools
# See [docs](https://docs.databricks.com/generative-ai/agent-framework/unstructured-retrieval-tools.html) for details

# # (Optional) Use Databricks vector search indexes as tools
# # See https://docs.databricks.com/generative-ai/agent-framework/unstructured-retrieval-tools.html


def _safe_parse_tool_arguments(raw_args: Any) -> dict:
    """Parse tool call arguments robustly.
    - Accepts dict (returns as-is) or JSON string.
    - Tolerates concatenated JSON objects (e.g., '}{') by selecting the last object.
    """
    if isinstance(raw_args, dict):
        return raw_args
    if not isinstance(raw_args, str):
        return {}
    s = raw_args.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Try to handle concatenated JSON objects like: '{...}{...}'
        if "}{" in s:
            # Try last object first
            try:
                return json.loads("{" + s.split("}{")[-1])
            except Exception:
                pass
            # Try as a list of objects and take the last one
            try:
                arr = json.loads("[" + s.replace("}{", "},{") + "]")
                if isinstance(arr, list) and arr:
                    return arr[-1]
            except Exception:
                pass
        # As a fallback, attempt to extract the first balanced JSON object
        depth = 0
        end = -1
        for i, ch in enumerate(s):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            try:
                return json.loads(s[:end])
            except Exception:
                pass
        # Give up and raise a clean error message
        raise json.JSONDecodeError("Unable to parse tool arguments", s, 0)


class ToolCallingAgent(ResponsesAgent):
    """
    Class representing a tool-calling Agent
    """

    def __init__(
        self,
        llm_endpoint: str,
        tools: list[ToolInfo],
        workspace_client: Optional[WorkspaceClient] = None,
    ):
        """Initializes the ToolCallingAgent with tools."""
        self.llm_endpoint = llm_endpoint
        self.workspace_client = workspace_client or WorkspaceClient()
        self.model_serving_client: OpenAI = (
            self.workspace_client.serving_endpoints.get_open_ai_client()
        )
        self._tools_dict = {tool.name: tool for tool in tools}

    def get_tool_specs(self) -> list[dict]:
        """Returns tool specifications in the format OpenAI expects."""
        return [tool_info.spec for tool_info in self._tools_dict.values()]

    @mlflow.trace(span_type=SpanType.TOOL)
    def execute_tool(self, tool_name: str, args: dict) -> Any:
        """Executes the specified tool with the given arguments."""
        return self._tools_dict[tool_name].exec_fn(**args)

    def call_llm(self, messages: list[dict[str, Any]]) -> Generator[dict[str, Any], None, None]:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="PydanticSerializationUnexpectedValue")
            for chunk in self.model_serving_client.chat.completions.create(
                model=self.llm_endpoint,
                messages=to_chat_completions_input(messages),
                tools=self.get_tool_specs(),
                stream=True,
            ):
                chunk_dict = chunk.to_dict()
                if len(chunk_dict.get("choices", [])) > 0:
                    yield chunk_dict

    def handle_tool_call(
        self,
        tool_call: dict[str, Any],
        messages: list[dict[str, Any]],
    ) -> ResponsesAgentStreamEvent:
        """
        Execute tool calls, add them to the running message history, and return a ResponsesStreamEvent w/ tool output
        """
        raw_args = tool_call.get("arguments", {})
        args = _safe_parse_tool_arguments(raw_args)
        result = str(self.execute_tool(tool_name=tool_call["name"], args=args))

        tool_call_output = self.create_function_call_output_item(tool_call["call_id"], result)
        messages.append(tool_call_output)
        return ResponsesAgentStreamEvent(type="response.output_item.done", item=tool_call_output)

    def call_and_run_tools(
        self,
        messages: list[dict[str, Any]],
        max_iter: int = 20,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        for _ in range(max_iter):
            last_msg = messages[-1]
            if last_msg.get("role", None) == "assistant":
                return
            elif last_msg.get("type", None) == "function_call":
                yield self.handle_tool_call(last_msg, messages)
            else:
                yield from output_to_responses_items_stream(
                    chunks=self.call_llm(messages), aggregator=messages
                )

        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item("Max iterations reached. Stopping.", str(uuid4())),
        )

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(output=outputs, custom_outputs=request.custom_inputs)

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        messages = to_chat_completions_input([i.model_dump() for i in request.input])
        if SYSTEM_PROMPT:
            messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT.format()})
        yield from self.call_and_run_tools(messages=messages)

    def predict_stream_local(self, question: str) -> Generator[dict, None, None]:
        """Stream a response for the given question (local convenience method).

        This wraps the ResponsesAgent predict_stream for easier use with FastAPI routes.

        Yields dicts with keys:
            - type: 'token', 'tool_call', 'done', or 'error'
            - content: token text (for type='token')
            - tool: tool info (for type='tool_call')
            - trace_id: MLflow trace ID (for type='done')
            - error: error message (for type='error')
        """
        input_msg = Message(role="user", content=question)
        request = ResponsesAgentRequest(input=[input_msg])

        try:
            for event in self.predict_stream(request):
                if event.type == "response.output_item.done":
                    item = event.item
                    item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)

                    if item_type == "function_call":
                        item_dict = item if isinstance(item, dict) else item.model_dump()
                        yield {
                            "type": "tool_call",
                            "tool": {
                                "name": item_dict.get("name"),
                                "arguments": item_dict.get("arguments"),
                            },
                        }
                    elif item_type == "function_call_output":
                        pass  # Tool output - already handled
                    elif item_type == "message":
                        item_dict = item if isinstance(item, dict) else item.model_dump()
                        content = item_dict.get("content", [])
                        if content and isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "output_text":
                                    yield {"type": "token", "content": c.get("text", "")}

                elif event.type == "response.content_part.delta":
                    delta = event.delta if hasattr(event, "delta") else None
                    if delta:
                        text = delta.get("text") if isinstance(delta, dict) else getattr(delta, "text", None)
                        if text:
                            yield {"type": "token", "content": text}

            # Done - get trace ID
            try:
                trace = mlflow.get_current_active_trace()
                trace_id = trace.info.request_id if trace else None
            except Exception:
                trace_id = None

            yield {"type": "done", "trace_id": trace_id}

        except Exception as e:
            yield {"type": "error", "error": str(e)}


# Log the model using MLflow
mlflow.openai.autolog()
AGENT = ToolCallingAgent(
    llm_endpoint=LLM_ENDPOINT_NAME, tools=TOOL_INFOS, workspace_client=WORKSPACE_CLIENT
)
mlflow.models.set_model(AGENT)


def get_agent() -> ToolCallingAgent:
    """Get the singleton AGENT instance."""
    return AGENT
