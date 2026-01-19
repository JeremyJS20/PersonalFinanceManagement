# FinOrbit - Personal Finance Management

FinOrbit is a premium, modern Personal Finance Management (PFM) application built with **Django** and **Tailwind CSS**. It helps users track their net worth, manage budgets, and visualize expenses in a clean, professional interface.

## Features

-   **Dashboard Overview**: Real-time view of Net Worth (Assets vs. Liabilities) and Monthly Budget progress.
-   **Expense Tracking**: Categorized spending breakdown with visual indicators.
-   **Security**: Minimalist, secure login interface.
-   **Hybrid Database**: Seamlessly switches between **PostgreSQL** (Production) and **SQLite** (Local Development) based on configuration.
-   **Modern UI**: Custom "FinOrbit" design system using Tailwind CSS (Teal/Blue aesthetic).

## Prerequisites

-   **Python 3.10+**
-   **Node.js & npm** (Required for Tailwind CSS)

## Installation

1.  **Clone or Download** the repository.
2.  **Navigate** to the project directory:
    ```bash
    cd financial_app
    ```
3.  **Create a Virtual Environment**:
    ```bash
    python -m venv venv
    ```
4.  **Activate the Environment**:
    -   Windows: `venv\Scripts\activate`
    -   Mac/Linux: `source venv/bin/activate`
5.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
6.  **Install Tailwind Dependencies**:
    ```bash
    python manage.py tailwind install
    ```

## Database Configuration

FinOrbit uses a smart configuration in `settings.py`:

-   **Local Mode (Default)**: If no database environment variables are set, it defaults to **SQLite**. No extra setup required.
-   **PostgreSQL Mode**: To use Postgres, create a `.env` file in the `financial_app` directory with:
    ```env
    DB_NAME=financial_db
    DB_USER=postgres
    DB_PASSWORD=your_password
    DB_HOST=localhost
    DB_PORT=5432
    ```

## Running the Application

1.  **Apply Migrations**:
    ```bash
    python manage.py migrate
    ```
2.  **Start the Server**:
    ```bash
    python manage.py runserver
    ```
3.  **Access the App**:
    Open [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/) in your browser.

## Development

-   **Tailwind Watcher**: To make CSS changes, run the Tailwind watcher in a separate terminal:
    ```bash
    python manage.py tailwind start
    ```
