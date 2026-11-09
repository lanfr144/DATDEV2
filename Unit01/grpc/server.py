"""
Book&Ride - Unit 01 - gRPC server on the SAME MongoDB books as the REST API.

    REST  (api/, port 8101)  : JSON over HTTP/1.1, readable with curl
    gRPC  (this, port 50101) : protobuf over HTTP/2, needs a generated client

books_pb2 / books_pb2_grpc are GENERATED from books.proto at image build time
(see Dockerfile): they are never written by hand and never committed.

Error handling = gRPC status codes, the equivalent of the HTTP codes:
    NOT_FOUND        ~ 404      INVALID_ARGUMENT ~ 400/422
    UNAVAILABLE      ~ 503      (MongoDB down)
"""
import os
from concurrent import futures
from urllib.parse import quote_plus

import grpc
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

import books_pb2
import books_pb2_grpc


def mongo_books():
    user = quote_plus(os.environ["MONGO_ROOT_USER"])
    password = quote_plus(os.environ["MONGO_ROOT_PASSWORD"])
    uri = f"mongodb://{user}:{password}@{os.environ['MONGO_HOST']}:{os.environ['MONGO_PORT']}/?authSource=admin"
    return MongoClient(uri, serverSelectionTimeoutMS=3000)[os.environ["MONGO_DB"]].books


def to_message(doc: dict) -> books_pb2.Book:
    """MongoDB document -> protobuf message (same idea as to_out() in the REST API)."""
    return books_pb2.Book(id=str(doc["_id"]), title=doc.get("title", ""),
                          author=doc.get("author", ""), year=int(doc.get("year") or 0),
                          isbn=doc.get("isbn", ""))


class BookService(books_pb2_grpc.BookServiceServicer):
    def __init__(self, books):
        self.books = books

    def GetBook(self, request, context):
        try:
            oid = ObjectId(request.id)
        except InvalidId:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "id is not a valid ObjectId")
        try:
            doc = self.books.find_one({"_id": oid})
        except PyMongoError:
            context.abort(grpc.StatusCode.UNAVAILABLE, "database unavailable")
        if doc is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "Book not found")
        return to_message(doc)

    def ListBooks(self, request, context):
        query = {"author": request.author} if request.author else {}
        limit = request.limit or 20
        try:
            for doc in self.books.find(query).sort("title").limit(limit):
                yield to_message(doc)          # each yield = one message on the stream
        except PyMongoError:
            context.abort(grpc.StatusCode.UNAVAILABLE, "database unavailable")


def serve() -> None:
    port = os.getenv("GRPC_PORT", "50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    books_pb2_grpc.add_BookServiceServicer_to_server(BookService(mongo_books()), server)
    server.add_insecure_port(f"[::]:{port}")   # plain HTTP/2 inside the Docker network (TLS: see U04)
    server.start()
    print(f'{{"level":"INFO","service":"books-grpc","action":"grpc_started","port":{port}}}', flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
