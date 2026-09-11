FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy project files
COPY . .

# Allocate Node memory for build
ENV NODE_OPTIONS="--max-old-space-size=2048"

# Build production bundle
RUN npm run build

# Use environment variable for port
ENV VITE_PORT=5173
EXPOSE 5173

# Serve production preview
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
