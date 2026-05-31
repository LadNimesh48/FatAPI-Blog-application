# def main():
#     print("Hello from fastapi-blog!")


# if __name__ == "__main__":
#     main()

from typing import Annotated
from fastapi import FastAPI, Request, HTTPException, status, Depends, Query
from fastapi.exceptions import RequestValidationError
# from fastapi.responses import JSONResponse 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from contextlib import asynccontextmanager
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler

from sqlalchemy import select, func, text
# from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import Base, engine, get_db

# Import routers
from routers import posts, users

from config import settings

# Base.metadata.create_all(bind=engine) # sync Way to run 

@asynccontextmanager
async def lifespan(_app:FastAPI):
    # StartUp for sql Lite
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    yield

    # shoutDown
    await engine.dispose()


# Create FastAPI instant
app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

# if we upload on local then use mount , if we uplaod on s3 then remove local mount 
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")


app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])

## Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    response.headers["X-Content-Type-Options"] = "nosniff"

    if "Referrer-Policy" not in response.headers:
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if request.url.hostname not in ("localhost", "127.0.0.1"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )

    return response


@app.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  detail="Database unavailable") from exc
    
    return {"status": "Healthy"}

        

@app.get("/", include_in_schema=False)
async def home(request : Request, db: Annotated[AsyncSession, Depends(get_db)]):

    count_result_withID = await db.execute(select(func.count(models.Post.id)))
    total_withID = count_result_withID.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .limit(settings.per_page_posts),
    )
    # print(query)
    posts = result.scalars().all()
    # print(posts)

    # return templates.TemplateResponse(request, 'home.html', {"posts": posts, "title": "home"})

    has_more = len(posts) < total_withID
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": posts,
            "title": "Home",
            "limit": settings.per_page_posts,
            "has_more": has_more,
        },
    )

@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(request : Request, post_id:int, db: Annotated[AsyncSession, Depends(get_db)]):


    query = select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id)
    result = await db.execute(query)
    posts = result.scalars().first()

    if posts:
        title = posts.title[:50]
        return templates.TemplateResponse(request, 'post.html', {"post": posts,  "title": title})

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post not found for  ID : {post_id}")

@app.get("/users/{user_id}/posts", include_in_schema=False)
async def user_post_page(request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    # print(user_id)
    # return 1

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not Found")
    
    count_result = await db.execute(
        select(func.count())
        .select_from(models.Post)
        .where(models.Post.user_id == user_id),
    )
    total = count_result.scalar() or 0
    
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id).order_by(models.Post.date_posted.desc()) .limit(settings.per_page_posts))
    posts = result.scalars().all()
    # print(posts)
    has_more = len(posts) < total

    # return templates.TemplateResponse(request, 'users_posts.html', {"posts": posts, "user": user,  "title": f"{ user.username }'s Posts" })

    return templates.TemplateResponse(
        request,
        "users_posts.html",
        {
            "posts": posts,
            "user": user,
            "title": f"{user.username}'s Posts",
            "limit": settings.per_page_posts,
            "has_more": has_more,
        },
    )


@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"title" : "Login"})

@app.get("/register", include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"title" : "Register"})

@app.get("/account", include_in_schema=False)
async def account_page(request: Request):
    return templates.TemplateResponse(request, "account.html", {"title" : "Account"})

@app.get("/forgot-password", include_in_schema=False)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"title": "Forgot Password"},
    )


@app.get("/reset-password", include_in_schema=False)
async def reset_password_page(request: Request):
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        {"title": "Reset Password"},
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    return response



@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):

    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)
    
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )