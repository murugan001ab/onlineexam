from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------- departments

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: Optional[str] = Field(default=None, max_length=50)
    # Only used by super_admin; ignored (forced to caller's college) for admin.
    college_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    code: Optional[str] = Field(default=None, max_length=50)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    name: str
    code: Optional[str] = None


# ------------------------------------------------------------------- classes

class ClassCreate(BaseModel):
    department_id: int
    name: str = Field(min_length=1, max_length=150)
    academic_year: Optional[str] = Field(default=None, max_length=20)
    section: Optional[str] = Field(default=None, max_length=20)


class ClassUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    academic_year: Optional[str] = Field(default=None, max_length=20)
    section: Optional[str] = Field(default=None, max_length=20)


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    department_id: int
    name: str
    academic_year: Optional[str] = None
    section: Optional[str] = None


# ------------------------------------------------------------ staff assignments

class StaffDepartmentAssign(BaseModel):
    department_id: int


class StaffDepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    department_name: str
    is_active: bool
    assigned_at: Optional[datetime] = None


class StaffClassAssign(BaseModel):
    class_id: int
    is_incharge: bool = False


class StaffClassUpdate(BaseModel):
    is_incharge: bool


class StaffClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    class_name: str
    is_incharge: bool
    assigned_at: Optional[datetime] = None
