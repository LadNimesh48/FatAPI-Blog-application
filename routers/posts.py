from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models

from database import get_db
from schemas import PostResponse, PostCreate, PostUpdate, PaginatedPostsResponse

from auth import CurrentUser


router = APIRouter()


@router.get("", response_model=PaginatedPostsResponse)
async def get_post(db: Annotated[AsyncSession, Depends(get_db)], skip: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 5):
    
    ## get_posts - count query
    # count_result_withoutID = await db.execute(select(func.count()).select_from(models.Post))
    # total_withoutID = count_result_withoutID.scalar() or 0
    # print(total_withoutID)

    count_result_withID = await db.execute(select(func.count(models.Post.id)))
    total_withID = count_result_withID.scalar() or 0
    # print(total_withID)

    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).order_by(models.Post.date_posted.desc()).offset(skip).limit(limit))
    posts = result.scalars().all()

    has_more = skip + len(posts) < total_withID
    
    # return posts
    return PaginatedPostsResponse(
        posts=[PostResponse.model_validate(post) for post in posts],
        total=total_withID,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):

    # print(current_user)
    # after implementation JWT Authontication not required to check user exist or not
    # result = await db.execute(select(models.User).where(models.User.id == post.user_id))
    # user = result.scalars().first()

    # if not user:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_post = models.Post(
        title = post.title,
        content= post.content,
        user_id = current_user.id,
        # user_id = post.user_id,
    )
    # print(new_post) 
    # return new_post
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])

    return new_post


@router.get("/{post_id}", response_model=PostResponse)
async def get_post_ByID(post_id:int, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    # print(post)

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post not found for  ID : {post_id}")

    return post
        

@router.put("/{post_id}", response_model=PostResponse)
async def update_post_full(post_data: PostCreate ,post_id:int, current_user : CurrentUser,  db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post not found for  ID : {post_id}")

    # after implementation JWT Authontication not required to check user exist or not
    # if post_data.user_id != post.user_id:

    #     result = await db.execute(select(models.User).where(models.User.id == post_data.user_id))
    #     user = result.scalars().first()

    #     if not user:
    #         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post not found for  ID : {post_id}")

    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not Authorized to update this Post")



    post.title = post_data.title
    post.content = post_data.content
    # post.user_id = current_user.id
    # post.user_id = post_data.user_id

    await db.commit()
    await db.refresh(post, attribute_names=["author"])

    return post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial(post_data: PostUpdate ,post_id:int, current_user : CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):

    print("post_data........",post_data)
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post not found for  ID : {post_id}")

    # if post_data.user_id != post.user_id:

    #     result = await db.execute(select(models.User).where(models.User.id == post_data.user_id))
    #     user = result.scalars().first()

    #     if not user:
    #         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post not found for  ID : {post_id}")

    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not Authorized to update this Post")
    
    update_data = post_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(post, field, value)

    # print(update_data.items())
    # return 1

    # # post.title = post_data.title
    # # post.content = post_data.content
    # # # post.user_id = post_data.user_id   

    await db.commit()
    await db.refresh(post, attribute_names=["author"])

    return post

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id:int, current_user : CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post not found for  ID : {post_id}")
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not Authorized to delete this Post")

    await db.delete(post)
    await db.commit()

