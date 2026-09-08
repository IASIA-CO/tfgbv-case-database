/**
 * Pin the post-login landing page for chosen roles.
 *
 * The app decides where to go after sign-in with:
 *     router.push(query.redirect || currentUser.last_page || '/content')
 * and rewrites last_page on every navigation via PATCH /users/me/track/page.
 * So a one-off write to last_page never holds — the next click overwrites it,
 * and the user lands wherever they happened to stop last time.
 *
 * That endpoint builds its UsersService without `accountability`, so it runs as
 * system and ignores field permissions; revoking update rights on last_page does
 * not stop it. It does still go through UsersService.updateOne, which emits this
 * filter hook, so rewriting the payload here is the one reliable intercept.
 *
 * Configure without rebuilding:
 *   LANDING_PAGE_ROUTE  route to pin        (default: the Insights dashboard below)
 *   LANDING_PAGE_ROLES  comma-separated role names (default: Subscriber)
 */
const DEFAULT_ROUTE = '/insights/99e6e7a7-ab82-4e20-8338-5a7a9d815d3b';
const DEFAULT_ROLES = 'Subscriber';

export default ({ filter }, { env, logger }) => {
	const route = env['LANDING_PAGE_ROUTE'] || DEFAULT_ROUTE;
	const roles = String(env['LANDING_PAGE_ROLES'] ?? DEFAULT_ROLES)
		.split(',')
		.map((r) => r.trim())
		.filter(Boolean);

	if (roles.length === 0) return;

	logger.info(`landing-page: pinning ${roles.join(', ')} to ${route}`);

	filter('users.update', async (payload, meta, context) => {
		// Only interested in the page-tracking write.
		if (!payload || payload.last_page === undefined) return payload;
		// Already correct - let it through rather than churn the row.
		if (payload.last_page === route) return payload;

		const keys = meta?.keys ?? [];
		if (keys.length === 0) return payload;

		try {
			const rows = await context
				.database('directus_users')
				.leftJoin('directus_roles', 'directus_users.role', 'directus_roles.id')
				.whereIn('directus_users.id', keys)
				.select('directus_roles.name as role_name');

			const isPinned = rows.some((r) => roles.includes(r.role_name));
			if (!isPinned) return payload;

			return { ...payload, last_page: route };
		} catch (error) {
			// Never let this break a page-tracking write; worst case the user
			// lands where they left off, which is the stock behaviour.
			logger.warn(`landing-page: role lookup failed, leaving last_page alone (${error.message})`);
			return payload;
		}
	});
};
