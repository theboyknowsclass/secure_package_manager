# Secure Package Manager

A secure package management system that processes package-lock.json files, validates packages, and manages approval workflows before publishing to secure repositories.

## Features

- **Authentication**: ADFS integration with mock IDP for development
- **Package Processing**: Upload and parse package-lock.json files
- **Validation Pipeline**: Download packages from npm and perform security validations
- **Workflow Management**: Track packages through requested → validated → approved → published states
- **Admin Interface**: Approve packages and manage the workflow
- **Secure Publishing**: Publish approved packages to configurable secure repositories

## Architecture

- **Backend**: Flask API with ADFS authentication
- **Frontend**: React application with Vite
- **Database**: PostgreSQL for package and user management
- **Containerization**: Docker and docker-compose for easy deployment

## Quick Start

1. Clone the repository
2. Configure environment variables (see `.env.example`)
3. Run `docker-compose up --build`
4. Access the application at `http://localhost:3000`

## Configuration

The application supports configuration for:
- ADFS endpoints and settings
- NPM proxy configuration
- Secure repository endpoints
- Database connection settings

## Development

- Mock IDP is included for development and testing
- Hot reloading enabled for both frontend and backend
- Database migrations included
