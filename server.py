"""HR MCP server for Northfield Coffee, a fictional coffee bean company."""

import os
from collections import Counter
from typing import Annotated, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.jwt import JWTVerifier, RSAKeyPair
from fastmcp.server.middleware import AuthMiddleware
from prefab_ui.components import Column, DataTable, DataTableColumn, Grid, Heading, Metric
from prefab_ui.components.charts import BarChart, ChartSeries
from pydantic import BaseModel, Field

ISSUER = os.getenv("JWT_ISSUER", "https://idp.example.com")
AUDIENCE = "hr-mcp"
HR_COMP_SCOPE = "hr:comp:read"
LOW_PTO_DAYS = 5

Department = Literal["Roastery", "Cafés", "Sourcing"]
EmployeeId = Annotated[int, Field(gt=0)]


class Employee(BaseModel):
    id: int
    name: str
    department: Department
    title: str
    salary: int
    pto_days_left: int

    def public_profile(self) -> dict:
        """Employee data without the salary."""
        return self.model_dump(exclude={"salary"})


STAFF = [
    # name, department, title, salary, PTO days left
    ("Thomas Vos", "Roastery", "Head Roaster", 82_000, 12),
    ("Hamza Simon", "Roastery", "Roast Profiler", 64_000, 3),
    ("Darius Scepterfield", "Roastery", "Quality Control Lead", 66_000, 15),
    ("Sandra Roberts", "Cafés", "Café Manager", 51_000, 4),
    ("Oscar Moreau", "Cafés", "Barista Lead", 42_000, 20),
    ("Abigail Martinez", "Cafés", "Barista", 36_000, 9),
    ("Eva Garcia", "Sourcing", "Green Coffee Buyer", 76_000, 8),
    ("Burcu Korkmaz", "Sourcing", "Supply Chain Analyst", 61_000, 2),
]

EMPLOYEES = [
    Employee(id=i, name=n, department=d, title=t, salary=s, pto_days_left=p)
    for i, (n, d, t, s, p) in enumerate(STAFF, start=1)
]


def get_employee(employee_id: int) -> Employee:
    for employee in EMPLOYEES:
        if employee.id == employee_id:
            return employee
    raise ToolError(f"No employee with id {employee_id}.")


JWKS_URI = os.getenv("JWKS_URI")
dev_keys: RSAKeyPair | None = None if JWKS_URI else RSAKeyPair.generate()


def build_auth() -> JWTVerifier:
    """Trust the company identity provider, or local test keys when JWKS_URI is unset."""
    if dev_keys is None:
        return JWTVerifier(jwks_uri=JWKS_URI, issuer=ISSUER, audience=AUDIENCE)
    return JWTVerifier(public_key=dev_keys.public_key, issuer=ISSUER, audience=AUDIENCE)


mcp = FastMCP("Northfield Coffee HR", auth=build_auth())


def create_dev_token(scopes: list[str]) -> str:
    if dev_keys is None:
        raise RuntimeError("Test tokens need local keys. Unset JWKS_URI.")
    return dev_keys.create_token(issuer=ISSUER, audience=AUDIENCE, scopes=scopes)


@mcp.tool
def list_employees(department: Department | None = None) -> list[dict]:
    """List employees, optionally filtered by department. Salaries are omitted."""
    return [
        e.public_profile() for e in EMPLOYEES if department is None or e.department == department
    ]


@mcp.tool
async def request_pto(
    employee_id: EmployeeId,
    days: Annotated[int, Field(ge=1, le=30)],
    ctx: Context,
) -> str:
    """Request PTO for an employee."""
    employee = get_employee(employee_id)
    if days > employee.pto_days_left:
        return f"Denied: {employee.name} only has {employee.pto_days_left} days left."
    employee.pto_days_left -= days
    await ctx.info(f"PTO approved for {employee.name}")
    return f"Approved: {days} days for {employee.name}."


@mcp.resource("hr://policies/pto")
def pto_policy() -> str:
    """The company PTO policy."""
    return (
        "Employees get 25 PTO days per year. "
        "Requests longer than 10 consecutive days need manager approval."
    )


@mcp.resource("hr://employees/{employee_id}")
def employee_profile(employee_id: EmployeeId) -> dict:
    """Public profile for one employee."""
    return get_employee(employee_id).public_profile()


@mcp.prompt
def onboarding_checklist(name: str, department: str) -> str:
    """Prompt template for a new starter's first-week checklist."""
    return f"Draft a first-week onboarding checklist for {name}, joining {department}."


@mcp.tool(app=True)
def hr_dashboard() -> Column:
    """Show headcount metrics, headcount by department and the staff directory."""
    by_dept = Counter(e.department for e in EMPLOYEES)
    columns = [
        ("name", "Name"),
        ("department", "Department"),
        ("title", "Title"),
        ("pto_days_left", "PTO left"),
    ]
    with Column(gap=4) as view:
        Heading("Northfield Coffee - People dashboard")
        with Grid(columns=3):
            Metric(label="Headcount", value=len(EMPLOYEES))
            Metric(label="Departments", value=len(by_dept))
            Metric(
                label=f"Low on PTO (<{LOW_PTO_DAYS} days)",
                value=sum(e.pto_days_left < LOW_PTO_DAYS for e in EMPLOYEES),
            )
        BarChart(
            data=[{"department": d, "headcount": n} for d, n in by_dept.items()],
            series=[ChartSeries(data_key="headcount", label="Headcount")],
            x_axis="department",
        )
        DataTable(
            columns=[DataTableColumn(key=k, header=h, sortable=True) for k, h in columns],
            rows=[e.public_profile() for e in EMPLOYEES],
            search=True,
        )
    return view


# Payroll: a separate group of tools, mounted under a namespace with its own access rule.
payroll = FastMCP("Payroll", middleware=[AuthMiddleware(auth=require_scopes(HR_COMP_SCOPE))])


@payroll.tool
def salary_report(department: Department) -> dict:
    """Average and total salary for a department."""
    salaries = [e.salary for e in EMPLOYEES if e.department == department]
    if not salaries:
        raise ToolError(f"No employees in department {department!r}.")
    return {
        "department": department,
        "headcount": len(salaries),
        "average": sum(salaries) // len(salaries),
        "total": sum(salaries),
    }


@payroll.tool
def employee_salary(employee_id: EmployeeId) -> dict:
    """Salary for a single employee."""
    employee = get_employee(employee_id)
    return {"name": employee.name, "salary": employee.salary}


mcp.mount(payroll, namespace="payroll")


if __name__ == "__main__":
    if dev_keys is not None:
        for label, scopes in [("HR", [HR_COMP_SCOPE]), ("STAFF", [])]:
            print(f"{label}_TOKEN={create_dev_token(scopes)}", flush=True)
    mcp.run(transport="http", host="0.0.0.0", port=8000)
