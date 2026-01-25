# Frontend Architecture - Initial Notes

## Architecture

The repo follows a client/server architecture typical for Databricks Apps:

client/ - Frontend (React/TypeScript)
server/ - Backend (likely FastAPI based on the Python stack and typical Databricks Apps patterns)
mlflow_demo/ - Core MLflow demo logic
setup/ - Deployment automation

## Layout (high-level)

Left-hand sidebar, left sixth of page dimension

- holds various pages
    - each sidebar has title, sub-text, and icon on the left
- PASTE IN NETRA (screenshots of sidebar and single sidebar item)

pages will contain the following actions but not limited to: 

- api calls to ML Flow for user to execute tasks in the app
    - accepts results from ML Flow and displays to user
        - TAKEAWAY: api routes with input/receive props

## Components

In General:

- shadcn cards
- dropdowns, text inputs (multi-line text mainly)

Critical:

- Multi-Line Text is returned from ML Flow
    - Two sections in the text response: `Original instructions:` and `Aligned Instructions`
        - Users will see the delta of what's different between the original and the aligned so any variances between sentences, new sentences should be highlighted as green.
            - How well we show the difference between the User’s input
- these components will need to use the props and types to send and receive data from ML Flow

## Web Hosting

- Databricks Hosted
    - don’t need to worry about user-auth

## Local-storage and State Persistence

- NONE needed between page loads or any other case

## Existing Git Repo

So there's an existing repo for the original MLflow app that's based on an email personalization use case. That use case is low value to show because everyone can just personalize an email through chat and MCP, so you don't need to go through this process for that. So instead, now we're going to change the plumbing in the backend to point to a different use case. And there's already a really good UI that I would just have to refactor and change the plumbing for in the backend to point to a different use case, details, and experiment. 

## Dev Planning

- [CLAUDE.md](http://CLAUDE.md) project memory file
    - what should go in this to help make coding with claude code chat efficient and project-specific?
    - ML Flow related functions will be all um, example in the repo in the directory ‘./mlflow_demo’