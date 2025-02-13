# Secure Voting System

## Overview
A secure, web-based voting system built with Flask, SQLAlchemy, and Tailwind CSS.

## Features
- Secure admin and voter authentication
- Dynamic election creation
- Unique voter key generation
- Real-time vote tracking
- Comprehensive results visualization

## Prerequisites
- Python 3.8+
- pip
- virtualenv (recommended)

## Local Development Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/voting-system.git
cd voting-system
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Initialize the database
```bash
python wsgi.py
```

5. Run the application
```bash
flask run
```

## Production Deployment

### Option 1: Gunicorn (Linux/macOS)
```bash
# Install gunicorn
pip install gunicorn

# Run the application
gunicorn --workers 3 --bind 0.0.0.0:5000 wsgi:app
```

### Option 2: Waitress (Windows)
```bash
# Install waitress
pip install waitress

# Run the application
waitress-serve --port=5000 wsgi:app
```

### Nginx Reverse Proxy Configuration (Optional)
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Environment Variables
Configure in `.env`:
- `FLASK_ENV`: Application environment
- `SECRET_KEY`: Secure random key
- `DATABASE_URL`: Database connection string
- `ADMIN_USERNAME`: Admin login username
- `ADMIN_PASSWORD`: Admin login password

## Security Notes
- Never share your `.env` file
- Use strong, unique passwords
- Regularly update dependencies
- Consider using HTTPS in production

## Troubleshooting
- Ensure all dependencies are installed
- Check file permissions
- Verify database connections

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
[Your License Here]
