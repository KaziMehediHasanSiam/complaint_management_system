Complaint Management System

This is a simple web-based Complaint Management System developed as part of our academic project using Flask and MySQL.The main goal of this project is to help users submit complaints online and allow staff/admin to manage and respond to them.

Project Features :
User Side -
Users can register and login to the system using a username and password
After login, users can submit complaints by providing title, description, category, and priority
Users can view only their own submitted complaints and check current complaint status

Staff / Admin Side :
Admin and staff can view all complaints submitted by users
Staff/admin can respond to complaints and update the complaint status (Open, In Progress, Resolved, etc.)
Admin can see complaint details along with user information

Dashboard & Reports :
Dashboard shows total complaints, open complaints, and resolved complaints
Recent complaints are shown on the dashboard for quick overview
Report page displays complaint count based on category, status, and priority

System Features :
Role-based access system (User, Staff, Admin)
Passwords are stored in encrypted format for security
Proper error handling for invalid pages and server errors


Technologies Used :
Python (Flask)
MySQL
HTML, CSS, Bootstrap
SQLAlchemy ORM

Notes :
Database tables are created automatically when the project runs
Admin account is created by default for testing purpose
This project focuses on functionality rather than UI design
