# RabbitReels

### A Distributed AI Video Platform

RabbitReels automates short-form video creation, editing, and publishing. Built for creators without traditional video editing skills, RabbitReels uses Python, FastAPI, Next.js, and RabbitMQ to enable rapid content generation from script to screen in under 5 minutes.

RabbitReels began as a personal project to automate short-form video creation, evolving into a platform serving over 50 active monthly users at it's peak. Initially facing scaling issues, RabbitReels adopted a Redis-based auto-scaling strategy, reducing processing time from 15 minutes down to 2-5 minutes per video.

Update (2026): RabbitReels is undergoing huge updates to boost processing speed and lower costs. May experience downtime late this Spring.
## Features

### Core Capabilities

* Fully automated AI-driven video pipeline.
* Scalable backend with auto-scaling using Redis, RabbitMQ, and Docker on GCP.
* Fast video rendering (2-5 minutes per video).
* Seamless publishing directly to YouTube.

### Security and Payments

* Secure authentication (Google OAuth 2.0, JWT, 2FA).
* Credits-based monetization via Stripe.
* Usage tracking and flexible subscription tiers.

## Technical Stack

* **Backend**: Python, FastAPI, PostgreSQL
* **Frontend**: Next.js, TypeScript
*  **Message Queue**: RabbitMQ
* **Job Management**: Redis
* **Containerization & Scaling**: Docker, Google Cloud Platform

## Architecture

The system balances usability, security, and sophistication:

* **FastAPI Web Layer**: Lightning-fast HTTP API with Google OAuth authentication
* **Script Generator**: AI-powered narrative creation tailored to your style
* **Video Creator**: MP4 rendering with customizable character voices
* **Publisher**: Automated YouTube upload
* **RabbitMQ**🐰🐇: Orchestrates message queue for the entire pipeline
* **Redis**: Real-time job tracking and session management
* **Auto-Scaling**: Dynamically scales workers based on demand

## Quick Start

### Prerequisites

* Docker
* Obtain Google OAuth credentials

### Setup Instructions

1. Clone repository:
```bash
git clone https://github.com/yourusername/RabbitReels.git
cd RabbitReels
```
2. Configure environment
3. Launch Docker services
