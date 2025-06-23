# backend/app/api/v1/api.py

from fastapi import APIRouter

from .endpoints import conversion_tasks

# Create a main router for the v1 API
api_router = APIRouter()

# Include the router from the conversion_tasks endpoint file.
# All routes defined in that file will now be part of this api_router.
# We can add tags to group them nicely in the OpenAPI documentation.
api_router.include_router(conversion_tasks.router, prefix="/tasks", tags=["Conversion Tasks"])

# If you were to add another set of endpoints, for example, for user management,
# you would create a `users.py` in the `endpoints` directory and include it here:
#
# from .endpoints import users
# api_router.include_router(users.router, prefix="/users", tags=["Users"])