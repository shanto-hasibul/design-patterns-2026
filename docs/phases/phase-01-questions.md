\# Phase 1 — Skeleton Questions



\## A. Pattern



\### 1. In your own words, what is a design pattern? What is it \*not\*?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> A design pattern is a common and reusable approach for solving a recurring software design problem. It gives developers a useful structure or idea that can be adapted to different applications. It is not ready-made code or a complete solution that must be copied exactly. A pattern should only be used when it helps solve a real design problem.



\### 2. Why do software developers use design patterns?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> Software developers use design patterns because they provide proven ways to solve common software design problems. They can make code easier to understand, maintain, and extend. They also give developers a shared way to discuss software structure and design decisions.



\### 3. What are the three main categories of design patterns?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> The three main categories of design patterns are Creational, Structural, and Behavioral patterns. Creational patterns focus on how objects are created. Structural patterns focus on how classes and objects are organized or connected. Behavioral patterns focus on how objects communicate and share responsibilities.



\## B. This phase of the application



\### 4. What are the three tiers in this project, and what is the responsibility of each tier?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> The three tiers are the frontend, backend, and database. The frontend is built with React and TypeScript and provides the user interface. The backend is built with FastAPI and handles API requests, application structure, and database communication. PostgreSQL is the database tier and is responsible for storing application data. In Phase 1, it only contains the Alembic migration tracking table because no business tables are created yet.



\### 5. How is the backend separated into layers, and what is the purpose of each layer?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> The backend is separated into domain, application, infrastructure, and interface/API layers. The domain layer will contain the main business entities and rules, but it is empty in Phase 1. The application layer will contain use cases and application logic, and it is also empty in this phase. The infrastructure layer manages settings, the database engine, sessions, and database connectivity. The interface/API layer handles the FastAPI endpoints, such as the health check. This separation makes the project easier to maintain and extend in later phases.





\### 6. What is the purpose of the `/health` endpoint in this phase?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> The `/health` endpoint checks whether the backend API and PostgreSQL database are working. The backend performs a simple `SELECT 1` query to test the database connection. When the database is reachable, it returns `status: "ok"` and `db: "ok"`. If the database connection fails, it reports a degraded status and `db: "fail"`. The frontend also uses this endpoint to show the health badge.





\### 7. Why is Alembic included even though Phase 1 has no business tables?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> Alembic is included in Phase 1 to set up and verify the database migration system before business tables are added. The baseline migration is intentionally empty, but running it proves that Alembic can connect to PostgreSQL and manage database versions correctly. This makes the project ready for Phase 2, where new tables such as `devices` can be added through migrations.





\## C. Compare / Scenarios



\### 8. What is the difference between a design pattern and a software architecture?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> Software architecture describes the overall structure of an application and how its major parts are organized. For example, our Smart Greenhouse uses a three-tier structure with frontend, backend, and database. A design pattern focuses on a more specific and recurring design problem inside the application. An application can use several design patterns within the same software architecture.





\### 9. Why is separation of concerns useful when the application grows?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> Separation of concerns keeps different responsibilities in different parts of the application. For example, the API layer handles HTTP requests while the infrastructure layer handles database connectivity and settings. This makes the code easier to understand, test, maintain, and change. It also helps us add new features in later phases without changing the whole project structure.





\### 10. Why is it useful to prepare the project structure before implementing design patterns?



> \[!NOTE]

> \*\*\*Your Answer\*\*\*

>

> Preparing the project structure first gives the application a clear foundation before adding design patterns and business features. The frontend, backend layers, database connection, migrations, and API structure are already working. Because of this, Phase 2 can focus on adding the `devices` functionality and Factory Method pattern without restructuring the whole project. It also makes it easier to see what problem the design pattern is actually solving.















