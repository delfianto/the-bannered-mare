---
title: Introduction
---

# Introduction

The Bannered Mare is an AI-powered platform for local roleplay sessions, inspired by
SillyTavern. It is a monorepo with two independent halves:

| Half | What it is |
|------|------------|
| Backend | Headless FastAPI service — providers, characters, prompts, RAG, streaming. |
| Frontend | Vue 3 SPA web client, talks to the backend via a typed `openapi-fetch` client. |

See [Quick Start](/guide/quick-start) to run both halves.
