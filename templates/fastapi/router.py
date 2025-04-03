from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..models.model import Model
from ..schemas.schema import ModelCreate, ModelRead, ModelUpdate
from ..services.service import ModelService

router = APIRouter(
    prefix="/api/resources",
    tags=["Resources"]
)


@router.get("/", response_model=List[ModelRead], status_code=status.HTTP_200_OK)
async def get_all_resources(
    skip: int = Query(0, description="Skip N records"),
    limit: int = Query(100, description="Limit the number of records returned"),
    db: Session = Depends(get_db)
):
    """
    Get all resources with pagination.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    service = ModelService(db)
    resources = service.get_all(skip=skip, limit=limit)
    return resources


@router.get("/{resource_id}", response_model=ModelRead, status_code=status.HTTP_200_OK)
async def get_resource(
    resource_id: int = Path(..., description="The ID of the resource to get"),
    db: Session = Depends(get_db)
):
    """
    Get a specific resource by ID.
    
    - **resource_id**: ID of the resource to retrieve
    """
    service = ModelService(db)
    resource = service.get_by_id(resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID {resource_id} not found"
        )
    return resource


@router.post("/", response_model=ModelRead, status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource: ModelCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new resource.
    
    - **resource**: Resource data
    """
    service = ModelService(db)
    try:
        new_resource = service.create(resource)
        return new_resource
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{resource_id}", response_model=ModelRead, status_code=status.HTTP_200_OK)
async def update_resource(
    resource: ModelUpdate,
    resource_id: int = Path(..., description="The ID of the resource to update"),
    db: Session = Depends(get_db)
):
    """
    Update an existing resource.
    
    - **resource_id**: ID of the resource to update
    - **resource**: Updated resource data
    """
    service = ModelService(db)
    try:
        updated_resource = service.update(resource_id, resource)
        if not updated_resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource with ID {resource_id} not found"
            )
        return updated_resource
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int = Path(..., description="The ID of the resource to delete"),
    db: Session = Depends(get_db)
):
    """
    Delete a resource.
    
    - **resource_id**: ID of the resource to delete
    """
    service = ModelService(db)
    result = service.delete(resource_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID {resource_id} not found"
        )
    return None 