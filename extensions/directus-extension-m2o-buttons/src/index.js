import InterfaceComponent from './interface.vue';

export default {
	id: 'm2o-buttons',
	name: 'Many to One (Create / Add Existing)',
	icon: 'arrow_right_alt',
	description:
		'A many-to-one that offers Create New and Add Existing as labelled buttons, ' +
		'the way a to-many field does, instead of the two small icons.',
	component: InterfaceComponent,
	types: ['uuid', 'string', 'integer', 'bigInteger'],
	localTypes: ['m2o'],
	group: 'relational',
	relational: true,
	options: ({ relations }) => [
		{
			field: 'template',
			name: '$t:display_template',
			type: 'string',
			meta: {
				interface: 'system-display-template',
				options: { collectionName: relations.m2o?.related_collection },
				width: 'full',
			},
		},
		{
			field: 'enableCreate',
			name: '$t:creating_items',
			schema: { default_value: true },
			meta: {
				interface: 'boolean',
				options: { label: '$t:enable_create_button' },
				width: 'half',
			},
		},
		{
			field: 'enableSelect',
			name: '$t:selecting_items',
			schema: { default_value: true },
			meta: {
				interface: 'boolean',
				options: { label: '$t:enable_select_button' },
				width: 'half',
			},
		},
		{
			field: 'createLabel',
			name: 'Create button label',
			type: 'string',
			schema: { default_value: 'Create New' },
			meta: { interface: 'input', width: 'half' },
		},
		{
			field: 'selectLabel',
			name: 'Select button label',
			type: 'string',
			schema: { default_value: 'Add Existing' },
			meta: { interface: 'input', width: 'half' },
		},
	],
};
