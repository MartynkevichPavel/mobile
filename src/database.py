import lancedb
from src.config import DB_PATH


class PhotoDatabase:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.db = None
        self.table = None
        self._connect()

    def _connect(self):
        # Новая версия LanceDB
        import lancedb
        self.db = lancedb.connect(self.db_path)
        try:
            self.table = self.db.open_table("photos")
            print("✅ Таблица 'photos' загружена")
        except:
            self._create_table()
            print("✅ Таблица 'photos' создана")

    def _create_table(self):
        import pyarrow as pa
        schema = pa.schema([
            ("id", pa.int64()),
            ("path", pa.string()),
            ("tags", pa.list_(pa.string())),
            ("embedding", pa.list_(pa.float64())),
        ])
        self.table = self.db.create_table("photos", schema=schema, mode="overwrite")

    def add_photo(self, photo_id: int, path: str, tags: list, embedding: list = None):
        if not embedding:
            embedding = [0.0] * 128

        import pyarrow as pa
        data = pa.table({
            "id": [photo_id],
            "path": [path],
            "tags": [tags],
            "embedding": [embedding],
        })
        self.table.add(data)

    def search_by_tags(self, search_tags: list) -> list:
        results = []
        for item in self.table.to_pandas().to_dict('records'):
            if any(tag in item['tags'] for tag in search_tags):
                results.append(item)
        return results

    def get_all_photos(self) -> list:
        return self.table.to_pandas().to_dict('records')