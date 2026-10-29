// =============================================================================
// Book&Ride - Unit 01 - the three queries of the DEVOP2 course, in mongosh
// =============================================================================
// Run: ./scripts/run_queries.sh      (same results as GET /logs/stats)
//
// NOW = 2025-09-18T10:00:00Z, imposed by the exercise: the dataset is from
// September 2025, so "the last 24 h" of the real clock would be empty.
// Window = [NOW - 24 h ; NOW[
// =============================================================================
db = db.getSiblingDB(process.env.MONGO_DB || 'bookandride');

const NOW = ISODate('2025-09-18T10:00:00Z');
const SINCE = new Date(NOW.getTime() - 24 * 60 * 60 * 1000);

if (db.logs.countDocuments() === 0) {
  print('ERROR: the logs collection is empty -> run ./scripts/load_logs.sh first');
  quit(1);
}

// Q1 - SQL: SELECT COUNT(*) FROM logs WHERE level='ERROR' AND timestamp >= SINCE AND timestamp < NOW
const q1 = db.logs.countDocuments({ level: 'ERROR', timestamp: { $gte: SINCE, $lt: NOW } });
print(`Q1 - ERROR logs between ${SINCE.toISOString()} and ${NOW.toISOString()}: ${q1}`);

// Q2 - SQL: SELECT timestamp, service, action FROM logs WHERE user_id='U12345' ORDER BY timestamp
print('Q2 - actions of user U12345:');
db.logs.find({ user_id: 'U12345' }, { _id: 0, timestamp: 1, service: 1, action: 1 })
  .sort({ timestamp: 1 }).forEach(d => print(`  ${d.timestamp.toISOString()}  ${d.service}  ${d.action}`));

// Q3 - SQL: SELECT DISTINCT service FROM logs WHERE level='WARN'
print('Q3 - services with at least one WARN: ' + db.logs.distinct('service', { level: 'WARN' }).sort().join(', '));

// Bonus - aggregation pipeline (GROUP BY): number of logs per service and level
print('Bonus - logs per service and level (includes the logs written by the API):');
db.logs.aggregate([
  { $group: { _id: { service: '$service', level: '$level' }, n: { $sum: 1 } } },
  { $sort: { '_id.service': 1, '_id.level': 1 } },
]).forEach(r => print(`  ${r._id.service.padEnd(14)} ${r._id.level.padEnd(5)} ${r.n}`));
