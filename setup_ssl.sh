#!/bin/bash
set -e

# Update package list and install Nginx & Certbot
echo "Installing Nginx and Certbot..."
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Create Nginx configuration
echo "Configuring Nginx for finpixe.com..."
cat << 'EOF' | sudo tee /etc/nginx/sites-available/finpixe.com
server {
    listen 80;
    server_name finpixe.com www.finpixe.com;

    # Route API requests to the backend (Docker)
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Route all other requests to the Vite frontend
    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for Vite
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable the site and restart Nginx
sudo ln -sf /etc/nginx/sites-available/finpixe.com /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# Run Certbot to generate and configure SSL
echo "Requesting SSL certificate..."
sudo certbot --nginx -d finpixe.com -d www.finpixe.com --non-interactive --agree-tos --register-unsafely-without-email

echo "=========================================="
echo "SSL Setup Complete! Visit https://finpixe.com"
echo "=========================================="
