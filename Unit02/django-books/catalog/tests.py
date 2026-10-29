"""python manage.py test  -> same scenarios as the FastAPI tests, Django style."""
from rest_framework.test import APITestCase

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965,
        "isbn": "978-0441013593", "price": "9.99", "tags": ["Sci-Fi", "classic"]}


class BookApiTests(APITestCase):
    def test_crud_cycle(self):
        r = self.client.post("/books/", DUNE, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["tags"], ["classic", "sci-fi"])
        url = f"/books/{r.json()['id']}/"
        self.assertEqual(self.client.patch(url, {"price": "12.50"}, format="json").json()["price"], "12.50")
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_validation_gives_400(self):
        for field, value in [("year", 2999), ("year", 1200), ("isbn", "123"), ("price", "0")]:
            r = self.client.post("/books/", {**DUNE, field: value}, format="json")
            self.assertEqual(r.status_code, 400, field)
            self.assertIn(field, r.json())
        self.client.post("/books/", DUNE, format="json")
        r = self.client.post("/books/", DUNE, format="json")        # same ISBN
        self.assertEqual(r.status_code, 400)
        self.assertIn("isbn", r.json())

    def test_search_ordering_pagination(self):
        for i in range(7):
            self.client.post("/books/", {**DUNE, "title": f"Book {i}", "year": 1990 + i,
                                         "isbn": f"978-000000000{i}"}, format="json")
        page = self.client.get("/books/", {"ordering": "-year"}).json()
        self.assertEqual(page["count"], 7)
        self.assertEqual(len(page["results"]), 5)                    # PAGE_SIZE
        self.assertEqual(page["results"][0]["year"], 1996)
        self.assertEqual(len(self.client.get("/books/", {"page": 2}).json()["results"]), 2)
        self.assertEqual(self.client.get("/books/", {"search": "book 3"}).json()["count"], 1)

    def test_health(self):
        self.assertEqual(self.client.get("/health/").json()["status"], "ok")
