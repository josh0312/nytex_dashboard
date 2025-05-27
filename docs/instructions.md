# Product Requirements Document: NyTex Fireworks Data Front-End

## 1. Project Overview
- **Objective**: Develop a web application to display sales reports, inventory data, and business insights for NyTex Fireworks, LLC.
- **Target Audience**: Internal team members at NyTex Fireworks.
- **Core Value Proposition**: Provide both high-level and detailed insights into business performance (historical and current), allowing the team to access essential information easily without relying on Square or spreadsheets.

---

## 2. Features and Functionality
### Key Features
1. **Interactive Data Tables**:
   - Sorting, filtering, and searching capabilities.
   - Drill-down functionality for detailed views.
2. **Dynamic Data Visualization**:
   - Mix of charts and tables to display data clearly.
3. **Real-Time Updates**:
   - Integrate with Square API for up-to-date sales and inventory data.
4. **Inventory Management**:
   - Overview of current inventory and detailed item information.
5. **Reporting**:
   - Generate and view various sales and inventory reports.
6. **Support Pages**:
   - Business Dashboard.
   - Location-Specific Dashboards (7 currently, scalable).
   - Staff Schedule.
   - Tools and Resources.
   - Link Library for quick access to company websites.

---

## 3. Technical Details
- **Backend Framework**: FastAPI.
- **Database Integration**: PostgreSQL with SQLAlchemy for ORM.
- **Data Sources**: 
  - PostgreSQL database for historical and inventory data.
  - Square API for real-time updates.
- **Authentication**: Integration with Office 365 IDs for secure access.

---

## 4. UI/UX Design

## UI Framework
- **ShadCN** will be used for building the user interface. It provides pre-built, accessible components styled with Tailwind CSS.
- Components such as tables, dropdowns, modals, tabs, and forms will streamline UI development while maintaining consistency across the application.
- ShadCN will integrate seamlessly with HTMX for dynamic, server-driven interactions.

### Key Pages
1. **Business Dashboard**:
   - High-level metrics on sales and performance trends.
2. **Location Dashboards**:
   - Detailed performance and inventory data for each location.
3. **Reports**:
   - Tools for generating and viewing sales, inventory, and staff reports.
4. **Items**:
   - Inventory management with item-level details.
5. **Staff Schedule**:
   - View and manage team schedules.
6. **Tools and Resources**:
   - Access essential business tools.
7. **Link Library**:
   - Quick access to important company websites.


### Styling
- **Framework**: Tailwind CSS for a clean and responsive design.
- **Responsive Design**: Fully functional on desktop, tablet, and smartphone devices.

---

## 5. Security
- **Authentication**: Use Office 365 IDs for access control.
- **Data Sensitivity**: No highly sensitive data; usability prioritized over extensive security measures.

---

## 6. Performance and Scalability
- **Expected Traffic**: 
  - Few users per day, with a maximum of 4 simultaneous users.
  - Anticipated growth over time.
- **Scalability**:
  - Lightweight and efficient system for current traffic.
  - Designed to scale resources with user growth.
- **Usability**: Focused on simplicity and intuitive design to ensure ease of use for all team members.

---

## 7. Success Metrics
- **User Adoption**: Measured by the number of internal team members using the platform regularly.
- **Efficiency Gains**: Reduction in time spent accessing and processing data.
- **Business Insights**: Enhanced decision-making enabled by accessible reports.

---

## 8. Timeline and Resources
- **Timeline**: No strict deadlines; progress can be made at a steady pace.
- **Team**: Single developer responsible for all aspects of development.

---

## 9. Development Roadmap
### Phase 1 (MVP)
- Implement Business and Location Dashboards.
- Develop Reports and Items pages.
- Integrate Office 365 authentication.

### Phase 2
- Add Staff Schedule, Tools, and Link Library pages.
- Optimize Square API integration for real-time updates.

### Phase 3
- Enhance filtering and drill-down capabilities.
- Refine UI/UX for simplicity and accessibility.
- Prepare for scaling as user growth increases.

---

## Additional Notes
- Use HTMX for a lightweight, server-driven application with minimal JavaScript.
- Real-time capabilities prioritized for critical data (sales and inventory updates).
- Tailwind CSS ensures responsive and aesthetically consistent design.

### Initial Structure
project-root/
│
├── app/
│   ├── __init__.py         # Initializes the Flask app
│   ├── logger.py           # Logging configuration
│   ├── models/             # SQLAlchemy models
│   │   ├── __init__.py     # Imports all models
│   │   ├── item.py         # Example: Item model
│   │   ├── routes/             # Flask routes
│   │   │   ├── __init__.py     # Imports all routes
│   │   │   ├── main.py         # Main routes
│   │   │   ├── api.py          # API-specific routes
│   │   ├── htmx/               # HTMX partials and components
│   │   │   ├── partials/       # HTMX partial HTML responses
│   │   │   ├── components/     # Reusable UI components (e.g., cards, modals)
│   │   ├── templates/          # HTML templates
│   │   │   ├── base.html       # Base layout
│   │   │   ├── index.html      # Homepage
│   │   │   ├── dashboard.html  # Dashboard
│   │   ├── static/             # Static files (TailwindCSS, JavaScript)
│   │   │   ├── css/
│   │   │   │   ├── styles.css  # TailwindCSS file
│   │   │   │   ├── js/
│   │   │   │   │   ├── htmx.min.js # HTMX library
│   │   │   │   │   ├── app.js      # Custom JavaScript
│   │   │   │   │   ├── img/            # Static images
│   │   │   ├── logs/                   # Logs directory
│   │   │   │   ├── app.log             # Log file
│   │   │   │   ├── logger.py           # Logger configuration
│   │   │   ├── migrations/             # Alembic migration files
│   │   │   │   ├── versions/           # Migration scripts
│   │   │   │   └── env.py              # Alembic environment file
│   │   │   ├── tests/                  # Unit and integration tests
│   │   │   │   ├── test_app.py         # Example tests
│   │   │   ├── .env                    # Environment variables
│   │   │   ├── config.py               # Flask configuration
│   │   │   ├── tailwind.config.js      # TailwindCSS configuration
│   │   │   ├── package.json            # Node.js package file
│   │   │   ├── requirements.txt        # Python dependencies
│   │   │   ├── Dockerfile              # Optional: Docker container setup
│   │   │   └── docker-compose.yml      # Optional: Docker for multi-container setup
│   │   └── run.py                  # Entry point for running the Flask app 