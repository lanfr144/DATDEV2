// =============================================================================
// Book&Ride - Unit 01 - seed: load logs.ndjson (dataset of the DEVOP2 course)
// =============================================================================
// Run automatically by the mongo image on the FIRST start of an empty volume
// (file mounted in /docker-entrypoint-initdb.d). Manual run, at any time:
//   ./scripts/load_logs.sh
//
// Two traps of the course exercise are avoided:
//   1. querying an empty collection silently returns 0 -> load BEFORE querying;
//   2. mongoimport keeps "timestamp" as a STRING, so {$gte: ISODate(...)}
//      never matches -> every timestamp is converted to a real BSON Date.
// Idempotent: upsert on (timestamp, service, user_id, action) -> no duplicates.
// =============================================================================
const fs = require('fs');

const target = db.getSiblingDB(process.env.MONGO_DB || 'bookandride');

const docs = fs.readFileSync('/seed/logs.ndjson', 'utf8')
  .split('\n')
  .filter(line => line.trim().length > 0)       // NDJSON: one document per line
  .map(line => {
    const doc = JSON.parse(line);
    doc.timestamp = new Date(doc.timestamp);    // String -> BSON Date
    return doc;
  });

const res = target.logs.bulkWrite(docs.map(doc => ({
  updateOne: {
    filter: { timestamp: doc.timestamp, service: doc.service,
              user_id: doc.user_id, action: doc.action },
    update: { $setOnInsert: doc },
    upsert: true,
  },
})));

print(`seed: ${docs.length} lines read, ${res.upsertedCount} inserted; ` +
      `${target.getName()}.logs holds ${target.logs.countDocuments()} documents`);
