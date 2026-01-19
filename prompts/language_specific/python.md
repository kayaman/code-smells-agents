# Python-Specific Review Guidelines

## Python Version
Target Python 3.10+ unless otherwise specified.

## Type Hints Priority

Python code at this company MUST use type hints. Check for:

```python
# ❌ Missing type hints
def process_user(user, options):
    ...

# ✅ Proper type hints
def process_user(user: User, options: ProcessOptions | None = None) -> Result:
    ...
```

Pay special attention to:
- Function parameters and return types
- Class attributes (use `ClassVar` or type annotations)
- Generic containers (`list[str]` not `list`)

## Common Python Anti-Patterns

### 1. Mutable Default Arguments
This is a CRITICAL issue in Python:
```python
# ❌ Bug waiting to happen
def add_item(item, items=[]):
    items.append(item)
    return items

# ✅ Correct
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append(item)
    return items
```

### 2. Bare Except Clauses
```python
# ❌ Catches SystemExit, KeyboardInterrupt, etc.
try:
    do_something()
except:
    pass

# ✅ Catch specific exceptions
try:
    do_something()
except (ValueError, KeyError) as e:
    logger.error("Operation failed", exc_info=True)
```

### 3. String Formatting in SQL
```python
# ❌ SQL Injection vulnerability
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ Parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### 4. Import Pollution
```python
# ❌ Namespace pollution
from module import *

# ✅ Explicit imports
from module import SpecificClass, specific_function
```

## Async Code Review

When reviewing async Python code:

1. **Check for blocking calls in async functions**
```python
# ❌ Blocking in async context
async def fetch_data():
    response = requests.get(url)  # Blocks the event loop!
    
# ✅ Proper async I/O
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

2. **Verify task handling**
```python
# ❌ Fire and forget (task can be garbage collected)
asyncio.create_task(background_work())

# ✅ Tracked tasks
task = asyncio.create_task(background_work())
background_tasks.add(task)
task.add_done_callback(background_tasks.discard)
```

## Data Classes & Pydantic

Prefer structured data over dictionaries:

```python
# ❌ Untyped, error-prone
user_data = {"name": "John", "age": 30, "email": "john@example.com"}

# ✅ Typed, validated
@dataclass
class User:
    name: str
    age: int
    email: str

# ✅ Even better for APIs (Pydantic)
class User(BaseModel):
    name: str
    age: int = Field(ge=0, le=150)
    email: EmailStr
```

## Testing Patterns

Look for:

1. **Proper pytest fixtures** vs inline setup
2. **No `time.sleep()` in tests** - use mocking or async wait
3. **Test isolation** - no shared state between tests
4. **Meaningful assertions** - not just "didn't crash"

```python
# ❌ Poor test
def test_user():
    user = User("test", 20, "test@test.com")
    assert user  # Meaningless

# ✅ Good test
def test_user_email_validation_rejects_invalid_format():
    with pytest.raises(ValidationError) as exc_info:
        User(name="test", age=20, email="not-an-email")
    assert "email" in str(exc_info.value)
```

## Company-Specific Python Standards

1. **Logging**: Use `structlog` with correlation IDs
```python
# ❌ 
print(f"User {user_id} logged in")
logger.info(f"User {user_id} logged in")

# ✅
logger.info("user_authenticated", user_id=user_id, method="oauth")
```

2. **Configuration**: Environment variables only
```python
# ❌
DATABASE_URL = "postgresql://localhost/db"

# ✅
DATABASE_URL = os.environ["DATABASE_URL"]
# or
DATABASE_URL = settings.database_url  # from pydantic-settings
```

3. **HTTP Clients**: Use company base client
```python
# ❌ Direct requests
response = requests.get(url, headers=headers)

# ✅ Company client (handles auth, retries, tracing)
response = await company_client.get(url)
```

## FastAPI Specific

For FastAPI endpoints:

1. **Always use Pydantic models for request/response**
2. **Use dependency injection for services**
3. **Async endpoints for I/O operations**
4. **Proper error handling with HTTPException**

```python
# ✅ Good FastAPI endpoint
@router.post("/users", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    try:
        return await service.create(user)
    except DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already exists")
```

## What Makes Python Code "Pythonic"

Encourage:
- List comprehensions (when readable)
- Context managers for resources
- `pathlib.Path` over `os.path`
- f-strings for formatting
- Walrus operator where it improves readability

Discourage:
- Overuse of classes when functions suffice
- Java-style getters/setters (use properties)
- Nested ternaries
- Complex one-liners that sacrifice readability
