# FinOrbit - Personal Finance Management

FinOrbit is a premium, modern Personal Finance Management (PFM) application built with **Django** and **Tailwind CSS**. It helps users track their net worth, manage budgets, and visualize expenses in a clean, professional interface.

## Features

-   **Dashboard Overview**: Real-time view of Net Worth (Assets vs. Liabilities) and Monthly Budget progress.
-   **Expense Tracking**: Categorized spending breakdown with visual indicators.
-   **Security**: Minimalist, secure login interface.
-   **Hybrid Database**: Seamlessly switches between **PostgreSQL** (Production) and **SQLite** (Local Development) based on configuration.
-   **Modern UI**: Custom "FinOrbit" design system using Tailwind CSS (Teal/Blue aesthetic).

## Prerequisites

-   **Python**: 3.14.2
-   **Node.js**: v25.2.1
-   **npm**: 11.6.4

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

- **PostgreSQL Mode**: FinOrbit now uses PostgreSQL exclusively. To connect, create a `.env` file in the `financial_app` directory with:
    ```env
    DB_NAME=postgres
    DB_USER=postgres
    DB_PASSWORD=your_password
    DB_HOST=your-project.supabase.co
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

## Development with PyCharm

1.  **Open Project**:
    -   Open PyCharm and select **Open**.
    -   Navigate to the `financial_app` folder (where `manage.py` is located) and click **OK**.

2.  **Configure Interpreter**:
    -   Go to **File > Settings > Project: financial_app > Python Interpreter**.
    -   Click the **Gear Icon** > **Add**.
    -   Select **Existing Environment**.
    -   Browse to your `venv\Scripts\python.exe` file and click **OK**.

3.  **Run Configuration (Robust Method)**:
    -   Go to **Run > Edit Configurations**.
    -   Click the **+** button (top left) and select **Python**.
    -   **Name**: `Django Runserver`
    -   **Script path**: `manage.py` (Browse to the file in your project).
    -   **Parameters**: `runserver`
    -   **Working directory**: `C:\Users\jsjer\OneDrive\Bureaublad\New folder\financial_app` (or your project root).
    -   **Environment variables**: `DJANGO_SETTINGS_MODULE=finance_project.settings`
    -   **Python interpreter**: Select your configured venv.
    -   Click **OK**.

4.  **Run**: Click the green **Play** button to start the server.
