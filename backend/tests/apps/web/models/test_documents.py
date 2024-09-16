import sys
import os
import logging
import pytest
import time
import json
from pydantic import BaseModel

from apps.web.models.documents import DocumentsTable, DocumentModel, DocumentForm, Document
from apps.web.internal.db import DB

# Constant definitions
TEST_USER_ID = "test_user"
TEST_DOC_NAME = "test_doc"
UPDATED_DOC_NAME = "updated_doc"
UPDATED_DOC_TITLE = "Updated Document"
NON_EXISTENT_DOC_NAME = "non_existent_doc"
TEST_TAGS = [
    {"name": "test_tag"},
    {"name": "test_tag_001"},
    {"name": "test_tag_002"}
]

@pytest.fixture(scope="module")
def documents_table():
    table = DocumentsTable(DB)
    yield table
    # Clean up test data
    Document.delete().execute()

@pytest.fixture
def sample_document_form():
    return DocumentForm(
        collection_name="test_collection",
        name=TEST_DOC_NAME,
        title="Test Document",
        filename="test.txt",
        content="This is a test document."
    )

def test_insert_new_doc(documents_table, sample_document_form):
    result = documents_table.insert_new_doc(TEST_USER_ID, sample_document_form)
    assert isinstance(result, DocumentModel)
    assert result.user_id == TEST_USER_ID
    assert result.name == sample_document_form.name

def test_get_doc_by_name(documents_table, sample_document_form):
    doc = documents_table.get_doc_by_name(sample_document_form.name)
    assert isinstance(doc, DocumentModel)
    assert doc.name == sample_document_form.name

def test_get_docs_by_tags(documents_table):
    # First insert a document with tags
    tagged_doc = DocumentForm(
        collection_name="tagged_collection",
        name="tagged_doc",
        title="Tagged Document",
        filename="tagged.txt",
        content=json.dumps({"tags": [TEST_TAGS[0]]})
    )
    documents_table.insert_new_doc(TEST_USER_ID, tagged_doc)

    docs = documents_table.get_docs_by_tags([TEST_TAGS[0]["name"]])
    assert len(docs) > 0
    assert any(doc.name == "tagged_doc" for doc in docs)

def test_get_doc_by_user_id(documents_table):
    docs = documents_table.get_doc_by_user_id(TEST_USER_ID)
    assert len(docs) > 0
    assert all(doc.user_id == TEST_USER_ID for doc in docs)

def test_get_docs(documents_table):
    docs = documents_table.get_docs()
    assert len(docs) > 0
    assert all(isinstance(doc, DocumentModel) for doc in docs)

def test_update_doc_by_name(documents_table, sample_document_form):
    # Insert multiple documents, each containing at least one tag
    for i, tag in enumerate(TEST_TAGS):
        form = DocumentForm(
            collection_name=f"collection_{i}",
            name=f"doc_{i}",
            title=f"Document {i}",
            filename=f"file_{i}.txt",
            content=json.dumps({"tags": [tag]})
        )
        documents_table.insert_new_doc(TEST_USER_ID, form)
    
    # Update document
    updated_form = DocumentForm(
        collection_name=sample_document_form.collection_name,
        name=UPDATED_DOC_NAME,
        title=UPDATED_DOC_TITLE,
        filename=sample_document_form.filename,
        content=sample_document_form.content
    )
    
    def update_and_assert(name, form, expected_name, expected_title):
        try:
            result = documents_table.update_doc_by_name(name, form)
            assert isinstance(result, DocumentModel)
            assert result.name == expected_name
            assert result.title == expected_title
        except Exception as e:
            assert result is None
            logging.exception(e)
    
    update_and_assert(sample_document_form.name, updated_form, UPDATED_DOC_NAME, UPDATED_DOC_TITLE)

def test_update_doc_content_by_name(documents_table, sample_document_form):
    # First insert a document
    documents_table.insert_new_doc(TEST_USER_ID, sample_document_form)
    
    updated_content = {"new_field": "new_value"}
    try:
        result = documents_table.update_doc_content_by_name(sample_document_form.name, updated_content)
        assert isinstance(result, DocumentModel)
        assert "new_field" in json.loads(result.content)
        assert json.loads(result.content)["new_field"] == "new_value"
    except Exception as e:
        assert result is None
        logging.exception(e)

def test_delete_doc_by_name(documents_table):
    result = documents_table.delete_doc_by_name(UPDATED_DOC_NAME)
    assert result is True
    assert documents_table.get_doc_by_name(UPDATED_DOC_NAME) is None
