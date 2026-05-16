from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import PrintTask, PrintRecipe, Product, Inventory
from backend.schemas import (
    PrintTaskCreate, PrintTaskUpdate, PrintTaskFailRequest,
    PrintTaskResponse, PrintTaskListResponse, PaginatedPrintTasksResponse,
    MessageResponse,
)
from backend.services.logger_service import log_business, log_error

router = APIRouter(prefix="/print-tasks", tags=["print-tasks"])


def _generate_task_no(db: Session) -> str:
    latest = db.query(func.max(PrintTask.id)).scalar() or 0
    return f"TASK-{latest + 1:03d}"


def _task_list_item(task: PrintTask) -> dict:
    recipe = task.recipe
    product = recipe.product if recipe else None
    return {
        "id": task.id,
        "task_no": task.task_no,
        "recipe_id": task.recipe_id,
        "status": task.status,
        "fail_reason": task.fail_reason,
        "retry_count": task.retry_count,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "notes": task.notes,
        "recipe_name": recipe.name if recipe else None,
        "product_name": product.name if product else None,
        "product_id": product.id if product else None,
        "output_qty": recipe.output_qty if recipe else None,
        "print_time_min": recipe.print_time_min if recipe else None,
    }


@router.get("", response_model=PaginatedPrintTasksResponse)
def list_print_tasks(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(PrintTask)
    if status:
        q = q.filter(PrintTask.status == status)
    total = q.count()
    items = (
        q.order_by(PrintTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_task_list_item(t) for t in items], "total": total}


@router.post("", response_model=PrintTaskResponse, status_code=201)
def create_print_task(data: PrintTaskCreate, db: Session = Depends(get_db)):
    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == data.recipe_id).first()
    if not recipe:
        raise HTTPException(404, "配方不存在")

    task = PrintTask(
        task_no=_generate_task_no(db),
        recipe_id=data.recipe_id,
        notes=data.notes,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    log_business("打印任务创建", task.task_no,
                 recipe=recipe.name, product_id=recipe.product_id)
    return task


@router.get("/{task_id}", response_model=PrintTaskResponse)
def get_print_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(PrintTask).filter(PrintTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "打印任务不存在")
    return task


@router.put("/{task_id}", response_model=PrintTaskResponse)
def update_print_task(task_id: int, data: PrintTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(PrintTask).filter(PrintTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "打印任务不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/start", response_model=PrintTaskResponse)
def start_print_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(PrintTask).filter(PrintTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "打印任务不存在")
    if task.status != "pending":
        raise HTTPException(400, f"只有待处理状态的任务可以开始，当前状态: {task.status}")

    task.status = "printing"
    task.started_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    log_business("打印任务开始", task.task_no)
    return task


@router.post("/{task_id}/complete", response_model=PrintTaskResponse)
def complete_print_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(PrintTask).filter(PrintTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "打印任务不存在")
    if task.status not in ("pending", "printing"):
        raise HTTPException(400, f"当前状态不可完成，状态: {task.status}")

    recipe = db.query(PrintRecipe).filter(PrintRecipe.id == task.recipe_id).first()
    if not recipe:
        raise HTTPException(404, "关联配方不存在")

    task.status = "done"
    task.completed_at = datetime.utcnow()

    recipe.print_count += 1

    inventory = db.query(Inventory).filter(
        Inventory.product_id == recipe.product_id
    ).first()
    if inventory:
        inventory.quantity += recipe.output_qty
    else:
        inventory = Inventory(
            product_id=recipe.product_id,
            quantity=recipe.output_qty,
        )
        db.add(inventory)

    db.commit()
    db.refresh(task)
    log_business("打印任务完成", task.task_no,
                 product_id=recipe.product_id, output_qty=recipe.output_qty,
                 print_count=recipe.print_count)
    return task


@router.post("/{task_id}/fail", response_model=PrintTaskResponse)
def fail_print_task(task_id: int, data: PrintTaskFailRequest = None, db: Session = Depends(get_db)):
    task = db.query(PrintTask).filter(PrintTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "打印任务不存在")
    if task.status not in ("pending", "printing"):
        raise HTTPException(400, f"当前状态不可标记失败，状态: {task.status}")

    task.status = "failed"
    task.fail_reason = data.fail_reason if data else None
    task.retry_count += 1
    db.commit()
    db.refresh(task)
    log_business("打印任务失败", task.task_no, reason=task.fail_reason)
    return task


@router.post("/{task_id}/cancel", response_model=PrintTaskResponse)
def cancel_print_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(PrintTask).filter(PrintTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "打印任务不存在")
    if task.status not in ("pending", "printing"):
        raise HTTPException(400, f"当前状态不可取消，状态: {task.status}")

    task.status = "cancelled"
    db.commit()
    db.refresh(task)
    log_business("打印任务取消", task.task_no)
    return task
