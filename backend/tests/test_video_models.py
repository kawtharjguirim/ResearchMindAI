"""Tables Source et Chunk : création, ordre des chunks, suppression en cascade, format de recherche."""
import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.project import Project  # noqa: F401  (table référencée par sources.project_id)
from app.models.source import Chunk, Source, SourceStatus, SourceType


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def nouvelle_source(**kw) -> Source:
    s = Source(user_id="u1", title="Conférence", filename="abc.mp4", language="fr", **kw)
    s.chunks = [Chunk(position=i, start=i * 40.0, end=i * 40.0 + 45, timestamp=f"t{i}", text=f"texte {i}")
                for i in (1, 0, 2)]
    return s


def test_tables_creees(db):
    tables = inspect(db.get_bind()).get_table_names()
    assert {"sources", "chunks"} <= set(tables)


def test_valeurs_par_defaut_et_ordre_des_chunks(db):
    db.add(nouvelle_source(segments=[{"start": 0.0, "end": 4.2, "text": "Bonjour."}]))
    db.commit()
    db.expire_all()
    s = db.scalars(select(Source)).one()
    assert s.status is SourceStatus.pending and s.source_type is SourceType.video
    assert s.error == "" and s.segments[0]["text"] == "Bonjour."
    assert [c.position for c in s.chunks] == [0, 1, 2]


def test_suppression_en_cascade_des_chunks(db):
    db.add(nouvelle_source())
    db.commit()
    db.delete(db.scalars(select(Source)).one())
    db.commit()
    assert db.scalars(select(Chunk)).all() == []


def test_as_search_chunk(db):
    s = nouvelle_source(url="https://youtu.be/x")
    db.add(s)
    db.commit()
    c = s.chunks[0].as_search_chunk()
    assert c["document_id"] == s.id and c["source"] == "https://youtu.be/x"
    assert c["source_type"] == "video" and c["language"] == "fr"
    assert set(c) >= {"chunk_id", "start", "end", "timestamp", "text", "title"}
