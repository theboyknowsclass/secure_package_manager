FROM node:18-alpine

# Install necessary packages
RUN apk add --no-cache python3 make g++

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Create storage directory for packages
RUN mkdir -p /app/storage/packages

# Expose port
EXPOSE 8080

# Start the registry
CMD ["npm", "start"]
