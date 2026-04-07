"""System tests for GraphQL gateway."""

import uuid

import pytest
from conftest import graphql_query


@pytest.mark.asyncio
async def test_query_books_empty(graphql_client):
    result = await graphql_query(
        graphql_client,
        "{ books { items { id title } continuationToken hasMore } }",
    )
    assert result["data"]["books"]["items"] == []
    assert result["data"]["books"]["hasMore"] is False


@pytest.mark.asyncio
async def test_create_and_query_book(graphql_client):
    mutation = """
    mutation {
        createBook(
            isbn: "9780000700001"
            title: "GraphQL Book"
            author: "GQL Author"
            genre: "Technology"
            publishedYear: 2024
            totalCopies: 3
        ) {
            id isbn title author genre publishedYear totalCopies availableCopies
        }
    }
    """
    result = await graphql_query(graphql_client, mutation)
    book = result["data"]["createBook"]
    assert book["isbn"] == "9780000700001"
    assert book["title"] == "GraphQL Book"
    assert book["availableCopies"] == 3

    query = f"""
    {{
        book(bookId: "{book["id"]}") {{
            id title isbn
        }}
    }}
    """
    result = await graphql_query(graphql_client, query)
    assert result["data"]["book"]["id"] == book["id"]


@pytest.mark.asyncio
async def test_query_books_with_data(graphql_client):
    for i in range(2):
        await graphql_query(
            graphql_client,
            f"""
            mutation {{
                createBook(
                    isbn: "978000070001{i}"
                    title: "Book {i}"
                    author: "Author"
                    genre: "Fiction"
                    publishedYear: 2024
                    totalCopies: 1
                ) {{ id }}
            }}
            """,
        )
    result = await graphql_query(
        graphql_client,
        "{ books { items { id } hasMore } }",
    )
    assert len(result["data"]["books"]["items"]) == 2


@pytest.mark.asyncio
async def test_query_books_pagination(graphql_client):
    for i in range(3):
        await graphql_query(
            graphql_client,
            f"""
            mutation {{
                createBook(
                    isbn: "978000070010{i}"
                    title: "Page Book {i}"
                    author: "Author"
                    genre: "Fiction"
                    publishedYear: 2024
                    totalCopies: 1
                ) {{ id }}
            }}
            """,
        )

    result = await graphql_query(
        graphql_client,
        "{ books(limit: 2) { items { id } continuationToken hasMore } }",
    )
    data = result["data"]["books"]
    assert len(data["items"]) == 2
    assert data["hasMore"] is True
    assert data["continuationToken"] is not None

    token = data["continuationToken"]
    result2 = await graphql_query(
        graphql_client,
        f'{{ books(limit: 2, continuationToken: "{token}") {{ items {{ id }} hasMore }} }}',
    )
    page2 = result2["data"]["books"]
    assert len(page2["items"]) == 1


@pytest.mark.asyncio
async def test_update_book(graphql_client):
    create_result = await graphql_query(
        graphql_client,
        """
        mutation {
            createBook(
                isbn: "9780000700021"
                title: "Original"
                author: "Author"
                genre: "Fiction"
                publishedYear: 2024
                totalCopies: 1
            ) { id }
        }
        """,
    )
    book_id = create_result["data"]["createBook"]["id"]

    update_result = await graphql_query(
        graphql_client,
        f"""
        mutation {{
            updateBook(bookId: "{book_id}", title: "Updated via GraphQL") {{
                id title
            }}
        }}
        """,
    )
    assert update_result["data"]["updateBook"]["title"] == "Updated via GraphQL"


@pytest.mark.asyncio
async def test_delete_book(graphql_client):
    create_result = await graphql_query(
        graphql_client,
        """
        mutation {
            createBook(
                isbn: "9780000700031"
                title: "To Delete"
                author: "Author"
                genre: "Fiction"
                publishedYear: 2024
                totalCopies: 1
            ) { id }
        }
        """,
    )
    book_id = create_result["data"]["createBook"]["id"]

    delete_result = await graphql_query(
        graphql_client,
        f"""
        mutation {{
            deleteBook(bookId: "{book_id}")
        }}
        """,
    )
    assert delete_result["data"]["deleteBook"] is True


@pytest.mark.asyncio
async def test_reserve_and_query(graphql_client):
    user_id = str(uuid.uuid4())
    create_result = await graphql_query(
        graphql_client,
        """
        mutation {
            createBook(
                isbn: "9780000700051"
                title: "Reserve Me"
                author: "Author"
                genre: "Fiction"
                publishedYear: 2024
                totalCopies: 3
            ) { id }
        }
        """,
    )
    book_id = create_result["data"]["createBook"]["id"]

    reserve_result = await graphql_query(
        graphql_client,
        f"""
        mutation {{
            reserveBooks(userId: "{user_id}", bookIds: ["{book_id}"]) {{
                id bookId userId status
            }}
        }}
        """,
    )
    reservations = reserve_result["data"]["reserveBooks"]
    assert len(reservations) == 1
    assert reservations[0]["status"] == "ACTIVE"

    res_id = reservations[0]["id"]
    query_result = await graphql_query(
        graphql_client,
        f"""
        {{
            reservation(reservationId: "{res_id}") {{
                id status userId
            }}
        }}
        """,
    )
    assert query_result["data"]["reservation"]["id"] == res_id


@pytest.mark.asyncio
async def test_return_reservation(graphql_client):
    user_id = str(uuid.uuid4())
    create_result = await graphql_query(
        graphql_client,
        """
        mutation {
            createBook(
                isbn: "9780000700061"
                title: "Return Me"
                author: "Author"
                genre: "Fiction"
                publishedYear: 2024
                totalCopies: 2
            ) { id }
        }
        """,
    )
    book_id = create_result["data"]["createBook"]["id"]

    reserve_result = await graphql_query(
        graphql_client,
        f"""
        mutation {{
            reserveBooks(userId: "{user_id}", bookIds: ["{book_id}"]) {{
                id status
            }}
        }}
        """,
    )
    res_id = reserve_result["data"]["reserveBooks"][0]["id"]

    return_result = await graphql_query(
        graphql_client,
        f"""
        mutation {{
            updateReservation(reservationId: "{res_id}", status: "RETURNED") {{
                id status
            }}
        }}
        """,
    )
    assert return_result["data"]["updateReservation"]["status"] == "RETURNED"


@pytest.mark.asyncio
async def test_query_reservations_with_filters(graphql_client):
    alice = str(uuid.uuid4())
    bob = str(uuid.uuid4())
    create_result = await graphql_query(
        graphql_client,
        """
        mutation {
            createBook(
                isbn: "9780000700071"
                title: "Filter Test"
                author: "Author"
                genre: "Fiction"
                publishedYear: 2024
                totalCopies: 5
            ) { id }
        }
        """,
    )
    book_id = create_result["data"]["createBook"]["id"]

    await graphql_query(
        graphql_client,
        f"""
        mutation {{
            reserveBooks(userId: "{alice}", bookIds: ["{book_id}"]) {{ id }}
        }}
        """,
    )
    await graphql_query(
        graphql_client,
        f"""
        mutation {{
            reserveBooks(userId: "{bob}", bookIds: ["{book_id}"]) {{ id }}
        }}
        """,
    )

    result = await graphql_query(
        graphql_client,
        f"""
        {{
            reservations(userId: "{alice}") {{
                items {{ id userId status }}
                hasMore
            }}
        }}
        """,
    )
    assert len(result["data"]["reservations"]["items"]) == 1
    assert result["data"]["reservations"]["items"][0]["userId"] == alice
