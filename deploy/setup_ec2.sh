#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Finprince EC2 Setup..."

# 1. System Updates and Dependencies
echo "Installing system dependencies..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx curl git mysql-client libmysqlclient-dev default-libmysqlclient-dev pkg-config build-essential

# 2. Node.js & PM2 (Using NVM for best compatibility)
echo "Installing Node.js and PM2..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# 3. Setup Python Virtual Environment (Backend)
echo "Setting up Python virtual environment..."
cd /home/ubuntu/finprince/backend

# Create .env from .env.example if missing
if [ ! -f ".env" ]; then
    echo "[INFO] Creating backend/.env from template..."
    cp .env.example .env
fi

# Ensure DJANGO_SECRET is set in .env
if ! grep -q "^DJANGO_SECRET=" .env || grep -q "^DJANGO_SECRET=$" .env; then
    NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    sed -i "s/^DJANGO_SECRET=.*/DJANGO_SECRET=${NEW_SECRET}/" .env
fi

python3 -m venv venv
python3 -c "open('requirements.txt', 'wb').write(open('requirements.txt', 'rb').read().replace(b'\x00', b''))"
./venv/bin/pip install --upgrade pip
./venv/bin/pip install python-dotenv celery django django-cors-headers djangorestframework djangorestframework_simplejwt django-environ django-filter pandas numpy pillow requests boto3 redis pymysql PyMySQL
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install gunicorn mysqlclient pymysql PyMySQL

# 4. Django Migrations and Static Files
echo "Running Django migrations and collecting static files..."
./venv/bin/python manage.py migrate
./venv/bin/python manage.py collectstatic --noinput



# 5. Build Frontend (React/Vite)
echo "Building Frontend..."
cd /home/ubuntu/finprince/frontend
npm install
npm run build

# 6. Configure Nginx
echo "Configuring Nginx..."
# Copy the config to sites-available and enable it
sudo cp /home/ubuntu/finprince/deploy/nginx.conf /etc/nginx/sites-available/finprince
# Remove default nginx config if exists
sudo rm -f /etc/nginx/sites-enabled/default
# Enable new config
sudo ln -sf /etc/nginx/sites-available/finprince /etc/nginx/sites-enabled/
# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# 7. Start Backend with PM2
echo "Starting Backend with PM2..."
cd /home/ubuntu/finprince
pm2 start deploy/ecosystem.config.js
pm2 save
pm2 startup systemd -u ubuntu --hp /home/ubuntu | tail -n 1 > /tmp/pm2_startup.sh
sudo bash /tmp/pm2_startup.sh

echo "=========================================================="
echo "Deployment Complete!"
echo "Your app should now be running via Nginx and PM2."
echo "Check Nginx status: sudo systemctl status nginx"
echo "Check PM2 status: pm2 status"
echo "Check PM2 logs: pm2 logs"
echo "=========================================================="
