"""
/books - the five HTTP methods of a REST resource (DATOP2 Unit 01).

    GET    /books          200  list (filter ?author=, ?limit=)
    GET    /books/{id}     200  one book            404 unknown id
    POST   /books          201  create + Location   409 ISBN already used, 422 invalid
    PUT    /books/{id}     200  full replacement    404, 409, 422
    PATCH  /books/{id}     200  partial update      404, 422
    DELETE /books/{id}     204  no body             404

Each handler stores a business action name in request.state.action; the
middleware of main.py writes it into the JSON log of the request.
"""
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from ..db import get_database
from ..schemas import BookIn, BookOut, BookPatch

router = APIRouter(prefix="/books", tags=["books"])


def to_out(doc: dict) -> BookOut:
    """MongoDB document -> JSON response (_id ObjectId -> id string)."""
    return BookOut(id=str(doc["_id"]), **{k: doc[k] for k in ("title", "author", "year", "isbn")})


def object_id(book_id: str, request: Request) -> ObjectId:
    """A malformed id cannot exist in the database: answer 404, not 500."""
    try:
        return ObjectId(book_id)
    except InvalidId:
        request.state.action = "book_not_found"
        raise HTTPException(status_code=404, detail="Book not found")


def not_found(request: Request) -> HTTPException:
    request.state.action = "book_not_found"
    return HTTPException(status_code=404, detail="Book not found")


def isbn_conflict(request: Request, isbn: str) -> HTTPException:
    request.state.action = "book_isbn_conflict"
    return HTTPException(status_code=409, detail=f"ISBN {isbn} already exists")


@router.get("", response_model=list[BookOut])
def list_books(request: Request, author: str | None = None,
               limit: int = Query(default=20, ge=1, le=100),
               db: Database = Depends(get_database)):
    request.state.action = "books_listed"
    query = {"author": author} if author else {}   # ?author= -> exact filter
    return [to_out(d) for d in db.books.find(query).sort("title").limit(limit)]


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: str, request: Request, db: Database = Depends(get_database)):
    doc = db.books.find_one({"_id": object_id(book_id, request)})
    if doc is None:
        raise not_found(request)
    request.state.action = "book_read"
    return to_out(doc)


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(book: BookIn, request: Request, response: Response,
                db: Database = Depends(get_database)):
    try:
        result = db.books.insert_one(book.model_dump())
    except DuplicateKeyError:
        raise isbn_conflict(request, book.isbn)
    request.state.action = "book_created"
    # HTTP cheat sheet: a 201 tells the client where the new resource lives
    response.headers["Location"] = f"/books/{result.inserted_id}"
    return to_out(db.books.find_one({"_id": result.inserted_id}))


@router.put("/{book_id}", response_model=BookOut)
def replace_book(book_id: str, book: BookIn, request: Request,
                 db: Database = Depends(get_database)):
    try:
        doc = db.books.find_one_and_replace({"_id": object_id(book_id, request)},
                                            book.model_dump(),
                                            return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        raise isbn_conflict(request, book.isbn)
    if doc is None:
        raise not_found(request)
    request.state.action = "book_replaced"
    return to_out(doc)


@router.patch("/{book_id}", response_model=BookOut)
def update_book(book_id: str, changes: BookPatch, request: Request,
                db: Database = Depends(get_database)):
    # exclude_unset: only the fields really sent by the client are changed
    fields = changes.model_dump(exclude_unset=True)
    oid = object_id(book_id, request)
    doc = (db.books.find_one_and_update({"_id": oid}, {"$set": fields},
                                        return_document=ReturnDocument.AFTER)
           if fields else db.books.find_one({"_id": oid}))
    if doc is None:
        raise not_found(request)
    request.state.action = "book_updated"
    return to_out(doc)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: str, request: Request, db: Database = Depends(get_database)):
    if db.books.delete_one({"_id": object_id(book_id, request)}).deleted_count == 0:
        raise not_found(request)
    request.state.action = "book_deleted"
    return Response(status_code=status.HTTP_204_NO_CONTENT)   # 204 = no body
