
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

@pytest.fixture(scope="function")
def session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()
