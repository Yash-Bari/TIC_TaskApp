# TIC TaskApp

A Task Management and Evaluation System built with Flask, TailwindCSS, and SQLite3.

## Features

- Google OAuth2.0 Authentication with domain restrictions
- Role-based access control (Admin, Coordinator, Student)
- Task creation and management
- Submission tracking and evaluation
- Automated notifications
- Leaderboard system
- Email integration

## Setup Instructions

1. Clone the repository:
```bash
git clone <repository-url>
cd tic-taskapp
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google OAuth2.0:
   - Go to the [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable the Google+ API
   - Configure the OAuth consent screen
   - Create OAuth 2.0 credentials (Web application)
   - Add authorized redirect URIs:
     * http://localhost:5000/login/google/authorized (for development)
     * https://your-domain.com/login/google/authorized (for production)

5. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in the required values:
     * SECRET_KEY
     * GOOGLE_OAUTH_CLIENT_ID
     * GOOGLE_OAUTH_CLIENT_SECRET
     * MAIL_USERNAME
     * MAIL_PASSWORD
     * MAIL_DEFAULT_SENDER

6. Initialize the database:
```bash
flask db upgrade
```

7. Run the application:
```bash
python run.py
```

## Project Structure

```
tic-taskapp/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── admin/
│   ├── coordinator/
│   ├── student/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
├── migrations/
├── tests/
├── .env.example
├── config.py
├── requirements.txt
└── run.py
```

## Role-Based Access

- Admin (tic.admin@srttc.ac.in):
  * User management
  * System access control
  * Leaderboard publication control

- Coordinator (tic.coordinator@srttc.ac.in):
  * Task management
  * Submission management
  * Evaluation system

- Student (@srttc.ac.in domain):
  * View and submit tasks
  * Track submissions
  * View leaderboard
  * Receive notifications

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
