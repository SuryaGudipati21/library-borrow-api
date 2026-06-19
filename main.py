from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator, EmailStr
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
)
from sqlalchemy.orm import Session, sessionmaker, declarative_base, relationship


engine = create_engine("sqlite:///library.db", connect_args = {"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autoflush = False, autocommit = False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key = True, index=True)
    title = Column(String, nullable = False)
    author = Column(String, nullable = False)
    total_copies = Column(Integer, default = 1, nullable = False)
    available_copies = Column(Integer, default=1, nullable = False)

    borrow_records = relationship("BorrowRecords", back_populates = "book")

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key = True, index = True)
    name = Column(String, nullable = False)
    email = Column(String, unique = True, nullable = False, index = True)

    borrow_records = relationship("BorrowRecords", back_populates = "member")

class BorrowRecords(Base):
    __tablename__ = "borrow_records"
    id = Column(Integer, primary_key = True, index = True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable = False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable = False)
    borrowed_at = Column(DateTime, default = datetime.utcnow)
    returned_at = Column(DateTime, nullable = True)

    book = relationship("Book", back_populates = "borrow_records")
    member = relationship("Member", back_populates = "borrow_records")

Base.metadata.create_all(bind=engine)


class BookCreate(BaseModel):
    title: str
    author: str
    total_copies: int = 1

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v : str) -> str:
        if not v.strip():
            raise ValueError("This field cannot be empty")
        return v.strip()
    
    @field_validator("total_copies")
    @classmethod
    def positive_copies(cls, v : int) -> int:
        if v < 1:
            raise ValueError("Toal copies must be atleas 1")
        return v
    
class MemberCreate(BaseModel):
    name: str
    email: EmailStr

    @field_validator("name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field cannot be empty")
        return v
    
class BorrowRequest(BaseModel):
    book_id: int
    member_id: int


app = FastAPI(title = "Library Borrowing System API")
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"]
)



#-------------------------------------Books Query------------------------------------
@app.get("/api/books")
def list_books(available_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Book)
    if available_only:
        query  = query.filter(Book.available_copies > 0)
    books = query.all()
    return[
        {
            "id": b.id, "title": b.title, "author": b.author, 
            "available_copies": b.available_copies, "total_copies": b.total_copies
        }
        for b in books
    ]

@app.post("/api/books", status_code = 201)
def create_book(payload: BookCreate, db: Session = Depends(get_db)):
    book = Book(
        title = payload.title,
        author = payload.author,
        total_copies = payload.total_copies,
        available_copies = payload.total_copies
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return {"id": book.id, "title": book.title, "author":book.author}

@app.delete("/api/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).get(book_id)
    if not book:
        raise HTTPException("Books not found")
    db.delete(book)
    db.commit()
    return {"message": "Book Deleted"}



#--------------------------------------Members Query-----------------------------------
@app.get("/api/members")
def list_members(db: Session = Depends(get_db)):
    members = db.query(Member).all()
    return [{"id": m.id, "name": m.name, "email": m.email} for m in members]


@app.post("/api/members")
def create_member(payload: MemberCreate, db: Session = Depends(get_db)):
    existing = db.query(Member).filter(Member.email==payload.email).first()
    if existing:
        raise HTTPException(status_code = 400, detail = "A member with this email already exists")
    member = Member(
        name = payload.name,
        email = payload.email
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return {"id":member.id, "name": member.name, "email": member.email}


@app.get("/api/members/{member_id}/history")
def member_history(member_id: int, db: Session = Depends(get_db)):
    member = db.query(Member).get(member_id)
    if not member:
        raise HTTPException(status_code = 404, detail = "Member not found")
    records = db.query(BorrowRecords).filter(BorrowRecords.member_id == member_id).all()
    return[
        {
            "record_id": r.id,
            "book_title": r.book.title,
            "borrowed_at": r.borrowed_at,
            "returned_at": r.returned_at,
            "currently_borrowed": r.returned_at is None,
        }
        for r in records
    ]



#-----------------------------------Borrow/Return Query--------------------------------
@app.post("/api/borrow", status_code = 201)
def borrow_book(payload: BorrowRequest, db: Session = Depends(get_db)):
    book = db.query(Book).get(payload.book_id)
    if not book:
        raise HTTPException(status_code = 404, detail = "Book not found")
    member = db.query(Member).get(payload.member_id)
    if not member:
        raise HTTPException(status_code = 404, detail = "Member not found")
    if book.available_copies <= 0:
        raise HTTPException(status_code = 400, detail = "No copies of this book are currently available")
    record = BorrowRecords(book_id = book.id, member_id = member.id)
    book.available_copies -= 1
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"message": "Book borrowed successfully", "record_id": record.id}

@app.post("/api/return/{record_id}")
def return_book(record_id: int, db: Session = Depends(get_db)):
    record = db.query(BorrowRecords).get(record_id)
    if not record:
        raise HTTPException(status_code = 404, detail = "Record not found")
    if record.returned_at is not None:
        raise HTTPException(status_code = 400, detail = "This book has already been returned")
    record.returned_at = datetime.utcnow()
    record.book.available_copies += 1
    db.commit()
    return {"message": "Books returned successfully"}



#------------------------------------------Root-----------------------------------------
@app.get("/")
def root():
    return {"message": "Library API is running. Visit /docs to explore endpoints."}