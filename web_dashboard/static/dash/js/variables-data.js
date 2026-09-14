/**
 * Shared `{variable}` tag list for the dashboard's message/embed editors.
 *
 * Single source of truth for variable-autocomplete.js and variable-chips.js — previously both scraped this from components/variables.html's modal,
 * which meant the feature only worked on pages that happened to include that modal. 
 * Keeping it as plain data here means every dashboard page gets the `{`-autocomplete/chip behavior automatically, with no per-page opt-in required.
 *
 * Keep this in sync with components/variables.html (the modal is still used elsewhere as a click-to-browse reference).
 *
 * This file is served minified as variables-data.min.js (see dash-links.html)
 * - there is no build step, so after editing THIS file you must regenerate
 * variables-data.min.js by hand before the change takes effect on the site:
 *
 *   cd web_dashboard/static/dash/js
 *   npx terser variables-data.js --compress --mangle --comments false -o variables-data.min.js
 *   node --check variables-data.min.js
 *
 * `node --check` only catches syntax errors - re-test in the browser if the
 * edit touched logic, not just comments/formatting.
 */
window.BOT_VARIABLES = [
  { tag: '{level}', desc: "The user's level (used for level up messages)" },
  { tag: '{prize}', desc: 'The prize of the giveaway' },
  { tag: '{index}', desc: 'The current number of opened/closed temporary voice channels' },
  { tag: '{age}', desc: 'The age of the user (used for birthday messages)' },

  { tag: '{user}', desc: "The user's username and display name" },
  { tag: '{user.mention}', desc: 'Mentions the user' },
  { tag: '{user.id}', desc: 'The id of the user' },
  { tag: '{user.name}', desc: 'The name of the user' },
  { tag: '{user.display_name}', desc: 'The display name of the user' },
  { tag: '{user.discriminator}', desc: 'The Discriminator of the user (0 as of March 4, 2024)' },
  { tag: '{user.avatar}', desc: 'A link to the avatar avatar' },
  { tag: '{user.avatar.url}', desc: 'A link to the avatar avatar' },
  { tag: '{user.display_avatar}', desc: 'A link to the avatar avatar' },
  { tag: '{user.bot}', desc: 'Whether the user is a bot' },

  { tag: '{server}', desc: 'The name of the server' },
  { tag: '{server.name}', desc: 'The name of the server' },
  { tag: '{server.id}', desc: 'The id of the server' },
  { tag: '{server.icon}', desc: 'The icon of the server' },
  { tag: '{server.icon.url}', desc: 'The icon of the server' },
  { tag: '{server.owner}', desc: 'The username of the server owner' },
  { tag: '{server.owner_id}', desc: 'The id of the server owner' },
  { tag: '{server.member_count}', desc: 'The total member of users on your server' },
  { tag: '{server.verification_level}', desc: 'The verification level of the server' },
];
