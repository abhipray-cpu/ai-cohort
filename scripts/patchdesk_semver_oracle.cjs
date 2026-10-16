// Independent npm-maintained semver implementation. No target project code is loaded.
const semver = require('../apps/patchdesk-web/node_modules/semver');
let input = '';
process.stdin.on('data', chunk => { input += chunk; });
function osv(record, name, version) {
  if (record.withdrawn || !semver.valid(version)) return null;
  const answers = [];
  for (const entry of record.affected || []) {
    if (entry.package?.ecosystem !== 'npm' || entry.package.name !== name) continue;
    if ((entry.versions || []).includes(version)) return true;
    for (const span of entry.ranges || []) {
      if (span.type !== 'SEMVER') { answers.push(null); continue; }
      let start = null;
      let valid = true;
      const intervals = [];
      for (const event of span.events || []) {
        if ('introduced' in event) {
          if (start !== null) valid = false;
          start = event.introduced;
          if (start !== '0' && !semver.valid(start)) valid = false;
        } else {
          const field = ['fixed', 'last_affected', 'limit'].find(k => k in event);
          if (!field || start === null || !semver.valid(event[field])) { valid = false; continue; }
          intervals.push(`${start === '0' ? '' : '>=' + start} ${field === 'last_affected' ? '<=' : '<'}${event[field]}`.trim());
          start = null;
        }
      }
      if (start !== null) intervals.push(start === '0' ? '*' : '>=' + start);
      answers.push(valid ? intervals.some(spec => semver.satisfies(version, spec, {includePrerelease:true})) : null);
    }
    if ((entry.versions || []).length && !(entry.ranges || []).length) answers.push(false);
  }
  return answers.includes(true) ? true : (!answers.length || answers.includes(null)) ? null : false;
}
process.stdin.on('end', () => {
  const data = JSON.parse(input);
  const answers = data.cases.map(c => c.kind === 'osv'
    ? osv(data.advisories[c.advisory], c.name, c.version)
    : semver.valid(c.version) && semver.validRange(c.spec)
      ? semver.satisfies(c.version, c.spec) : null);
  process.stdout.write(JSON.stringify({implementation:'npm node-semver',version:require('../apps/patchdesk-web/node_modules/semver/package.json').version,answers}));
});
