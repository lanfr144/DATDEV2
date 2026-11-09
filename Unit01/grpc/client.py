"""
Book&Ride - Unit 01 - gRPC client: the same questions as rest_client.py, in gRPC.

Run it inside the image (the generated code is there):
    docker compose --profile grpc run --rm grpc python client.py [author]

The client calls methods as if they were LOCAL functions (stub.GetBook(...)):
the generated stub hides HTTP/2, serialisation and errors -> "RPC".
"""
import os
import sys

import grpc

import books_pb2
import books_pb2_grpc

TARGET = os.getenv("GRPC_TARGET", "grpc:50051")


def main() -> int:
    author = sys.argv[1] if len(sys.argv) > 1 else ""
    with grpc.insecure_channel(TARGET) as channel:
        stub = books_pb2_grpc.BookServiceStub(channel)

        print(f"1. ListBooks(author={author!r}) - server streaming:")
        books = list(stub.ListBooks(books_pb2.ListBooksRequest(author=author, limit=5), timeout=5))
        for b in books:
            print(f"   {b.id}  {b.title} ({b.author}, {b.year})")
        if books:
            b = stub.GetBook(books_pb2.GetBookRequest(id=books[0].id), timeout=5)
            print(f"2. GetBook({b.id}) - unary: {b.title}")
            print(f"   size on the wire: {len(b.SerializeToString())} bytes of protobuf (binary)")

        for bad, label in (("0" * 24, "unknown id"), ("not-an-id", "malformed id")):
            try:
                stub.GetBook(books_pb2.GetBookRequest(id=bad), timeout=5)
            except grpc.RpcError as err:   # gRPC status code instead of an HTTP code
                print(f"3. GetBook({label}) -> {err.code().name}: {err.details()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
