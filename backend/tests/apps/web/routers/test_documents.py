import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from apps.web.routers.documents import router, Documents, Staffs
from apps.web.models.documents import DocumentForm, DocumentUpdateForm, DocumentResponse
from utils.utils import get_current_user, get_admin_user
import time
import json

# 创建一个 FastAPI 应用并挂载路由
app = FastAPI()
app.include_router(router)

# 创建测试客户端
client = TestClient(app)

# 模拟普通用户数据
class MockUser:
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role

mock_user = MockUser(id="test_user_id", email="test@example.com", role="user")
mock_admin = MockUser(id="admin_user_id", email="admin@example.com", role="admin")

# 修改模拟文档数据
mock_doc = MagicMock()
mock_doc.collection_name = "test_collection"
mock_doc.name = "test_doc"
mock_doc.title = "Test Document"
mock_doc.filename = "test.txt"
mock_doc.content = json.dumps({"tags": [{"name": "test_tag"},{"name": "test_tag001"}]})
mock_doc.user_id = "test_user_id"
mock_doc.timestamp = int(time.time())
mock_doc.model_dump.return_value = {
    "collection_name": mock_doc.collection_name,
    "name": mock_doc.name,
    "title": mock_doc.title,
    "filename": mock_doc.filename,
    "content": mock_doc.content,
    "user_id": mock_doc.user_id,
    "timestamp": mock_doc.timestamp
}

@pytest.fixture(autouse=True)
def mock_dependencies():
    # 模拟普通用户
    def mock_get_current_user():
        return mock_user

    # 模拟管理员用户
    def mock_get_admin_user():
        return mock_admin

    # 替换依赖
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_admin_user] = mock_get_admin_user

    yield

    # 清理依赖覆盖
    app.dependency_overrides.clear()

@pytest.fixture
def mock_documents():
    with patch("apps.web.routers.documents.Documents") as mock:
        mock.get_docs.return_value = [mock_doc]
        mock.get_doc_by_name.return_value = None  # 初始时文档不存在
        mock.insert_new_doc.return_value = mock_doc
        mock.update_doc_by_name.return_value = mock_doc
        mock.delete_doc_by_name.return_value = True
        mock.get_docs_by_tags.return_value = [mock_doc]  # 确保返回非空列表
        yield mock

@pytest.fixture
def mock_staffs():
    with patch("apps.web.routers.documents.Staffs") as mock:
        mock.get_staff_by_email.return_value = {"emp_type": "faculty"}
        yield mock

def test_get_documents(mock_documents, mock_staffs):
    response = client.get("/")
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert response.json()[0]["name"] == "test_doc"
    assert "collection_name" in response.json()[0]
    assert "title" in response.json()[0]
    assert "filename" in response.json()[0]
    assert "user_id" in response.json()[0]
    assert "timestamp" in response.json()[0]
    assert isinstance(response.json()[0]["timestamp"], int)

def test_create_new_doc(mock_documents):
    doc_form = DocumentForm(
        collection_name="test_collection",
        name="new_doc",
        title="New Document",
        filename="new.txt",
        content="This is a new document."
    )
    response = client.post("/create", json=doc_form.model_dump())
    assert response.status_code == 200
    assert response.json()["name"] == "test_doc"
    assert "collection_name" in response.json()
    assert "title" in response.json()
    assert "filename" in response.json()
    assert "user_id" in response.json()
    assert "timestamp" in response.json()
    assert isinstance(response.json()["timestamp"], int)

    # 测试创建已存在的文档
    mock_documents.get_doc_by_name.return_value = mock_doc
    response = client.post("/create", json=doc_form.model_dump())
    assert response.status_code == 400
    assert "detail" in response.json()

# 其他测试函数类似修改...

def test_create_new_doc_already_exists(mock_documents):
    mock_documents.get_doc_by_name.return_value = mock_doc
    doc_form = DocumentForm(
        collection_name="test_collection",
        name="existing_doc",
        title="Existing Document",
        filename="existing.txt",
        content="This document already exists."
    )
    response = client.post("/create", json=doc_form.model_dump())  # 使用 model_dump() 替代 dict()
    assert response.status_code == 400
    assert "detail" in response.json()
