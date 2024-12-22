# Prodctivity Pal

## Overview

**Prodctivit Pal** is an intelligent task scheduling and management system designed to overcome the limitations of traditional scheduling tools by providing flexibility and personalization. The system leverages a modular architecture to deliver efficient task planning, dynamic rescheduling, and habit-based optimization.

Key features of **PAL** include:

- Modular Design

   The system is built around three core modules:

  - **Habit Module**: Extracts and analyzes user habits to identify work patterns and productivity peaks.
  - **Scheduler Module**: Breaks down tasks into actionable subtasks and assigns them to optimal time slots.
  - **Rescheduler Module**: Dynamically adjusts task schedules based on real-time user feedback.

- **Data Storage and Real-Time Updates**: Utilizes MongoDB for efficient and scalable data management.

- **Dynamic Iterative Scheduling**: Continuously optimizes task arrangements to adapt to users’ changing needs and preferences.

Please note: this project is currently only supported on Apple systems (macOS).

## Quick Start

1. **Set Up Python Environment and Install Dependencies of OS-Copilot**

2. **Other Dependencies:**

   ```shell
   python -m pip install "pymongo[srv]"
   pip install --quiet sentence-transformers pymongo einops
   npm install electron
   ```

3. **Set OpenAI API Key:** Configure your OpenAI API key in .env

4. **Set Mongodb Atlas:** Replace `<username>`, `<password>`, and `<cluster-url>` with your Atlas credentials in `CONNECTION_STRING` in .env

   ```shell
   CONNECTION_STRING = "mongodb+srv://<username>:<password>@<cluster-url>/myDatabase?retryWrites=true&w=majority"
   ```

5. **Start server and front-end interface**
   ```shell
   cd productivity_pal
   python server.py #server
   npm start #front-end interface
   ```

   

## Feature Additions to OS-Copilot

This project builds upon the original **oscopilot** framework and introduces several enhancements across the front-end interface, agent capabilities, and database design. Below is a detailed breakdown of the added functionalities:

------

#### **1. Front-End Interface**

The front-end interface has been enhanced to provide better user interaction with tasks and schedules:

- **Module**: `oscopilot/productivity_pal`
- Functionality
  - **Task Management**: Users can now easily add, delete, and describe tasks through an intuitive interface.
  - **Schedule Retrieval**: Fetch the current task schedule directly from the database, enabling seamless integration with the user's workflow.

------

#### **2. Agent Functionalities**

The agent has been significantly expanded with advanced modules to support task scheduling and behavior analysis:

- **Habit Extraction**
  - **Module**: `oscopilot/modules/habit_tracker`
  - Functionality
    - Analyzes historical schedule data to extract user behavior patterns.
    - Identifies tasks' usual durations based on the extracted habits.
- **Task Planner**
  - **Module**: `oscopilot/modules/planner/task_planner.py`
  - Functionality
    - Accepts tasks with details such as name, description, and deadlines.
    - Performs **task decomposition**, breaking a task into smaller subtasks with estimated durations.
    - Uses the past 7 days of habit data and existing schedules to perform **task scheduling**, assigning time slots for each subtask.
- **Scheduler and Rescheduler**
  - **Module**: `oscopilot/modules/schedule_maker`
  - Functionality
    - Automatically integrates planned subtasks into the user's calendar app.
    - Supports dynamic adjustments by rescheduling all tasks before a specific date when plans change.

------

#### **3. Database Design**

The database structure has been extended to efficiently store and manage user data:

- **Module**: `oscopilot/utils/database.py`
- Functionality
  - Stores user habit data and schedule records.
  - Provides robust Create, Read, Update, and Delete (CRUD) operations for seamless data management.

