// Runs once on a fresh data volume via /docker-entrypoint-initdb.d.
// To re-run: `docker compose down -v && ./scripts/mongo-setup.sh`

const VECTOR_DB = 'zi-growth-vectors';   // <-- rename if you want a different vector-db name
const VECTOR_COLLECTION = 'embeddings';
const EMBEDDING_DIMS = 1536;             // match your embedding model

const DATABASES = [
  'zi-growth-signup',
  VECTOR_DB,
  'ce-users',
  'zi-lite-signup',
  'gtm-user-preferences',
];

// MongoDB creates databases lazily on first write.
// Add a marker collection to each so `show dbs` reflects them immediately.
DATABASES.forEach((name) => {
  const target = db.getSiblingDB(name);
  if (!target.getCollectionNames().includes('_init')) {
    target.createCollection('_init');
  }
});

// Vector search index on the vector db only.
const vectors = db.getSiblingDB(VECTOR_DB);
if (!vectors.getCollectionNames().includes(VECTOR_COLLECTION)) {
  vectors.createCollection(VECTOR_COLLECTION);
}

const existing = vectors.getCollection(VECTOR_COLLECTION).getSearchIndexes();
if (!existing.some((i) => i.name === 'vector_index')) {
  vectors.getCollection(VECTOR_COLLECTION).createSearchIndex(
    'vector_index',
    'vectorSearch',
    {
      fields: [{
        type: 'vector',
        path: 'embedding',
        numDimensions: EMBEDDING_DIMS,
        similarity: 'cosine',
      }],
    },
  );
}

print(`Initialized ${DATABASES.length} databases.`);
print(`Vector index created on ${VECTOR_DB}.${VECTOR_COLLECTION}.`);
