<template>
	<v-notice v-if="!relatedCollection" type="warning">
		This field has no relationship configured.
	</v-notice>

	<div v-else class="m2o-buttons">
		<div v-if="hasValue" class="selected">
			<render-template
				:collection="relatedCollection"
				:item="displayItem"
				:template="resolvedTemplate"
			/>
			<div class="spacer" />
			<v-icon v-if="!disabled" v-tooltip="'Edit'" name="edit" clickable @click="editActive = true" />
			<v-icon v-if="!disabled" v-tooltip="'Clear'" name="close" clickable @click="deselect" />
		</div>

		<!-- Empty state matching the built-in m2m list, so a to-one relation and a
		     to-many relation read as the same component on the same form. -->
		<v-notice v-else>No item selected</v-notice>

		<!-- No icons and small: matches the built-in m2m buttons, and keeps both on one
		     row inside a half-width field instead of wrapping into a stack. -->
		<div v-if="!disabled" class="actions">
			<v-button v-if="enableCreate" small @click="createActive = true">
				{{ createLabel || 'Create New' }}
			</v-button>
			<v-button v-if="enableSelect" small @click="selectActive = true">
				{{ selectLabel || 'Add Existing' }}
			</v-button>
		</div>

		<!-- Create: primary-key "+" stages a new related item on the parent, so it is
		     written in the same save as the case. Mirrors the built-in m2o. -->
		<drawer-item
			:active="createActive"
			:collection="relatedCollection"
			primary-key="+"
			:edits="{}"
			:circular-field="circularField"
			@input="onDrawerInput"
			@update:active="createActive = $event"
		/>

		<!-- Edit the currently linked item. -->
		<drawer-item
			:active="editActive"
			:collection="relatedCollection"
			:primary-key="editPrimaryKey"
			:edits="stagedEdits"
			:circular-field="circularField"
			@input="onDrawerInput"
			@update:active="editActive = $event"
		/>

		<drawer-collection
			:active="selectActive"
			:collection="relatedCollection"
			:selection="selection"
			:filter="filter"
			@input="onSelect"
			@update:active="selectActive = $event"
		/>
	</div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useApi, useStores } from '@directus/extensions-sdk';

const props = defineProps({
	value: { type: [String, Number, Object], default: null },
	collection: { type: String, required: true },
	field: { type: String, required: true },
	template: { type: String, default: null },
	disabled: { type: Boolean, default: false },
	enableCreate: { type: Boolean, default: true },
	enableSelect: { type: Boolean, default: true },
	createLabel: { type: String, default: 'Create New' },
	selectLabel: { type: String, default: 'Add Existing' },
	filter: { type: Object, default: null },
});

const emit = defineEmits(['input']);

const api = useApi();
const { useRelationsStore, useCollectionsStore, useFieldsStore } = useStores();
const relationsStore = useRelationsStore();
const collectionsStore = useCollectionsStore();
const fieldsStore = useFieldsStore();

const createActive = ref(false);
const editActive = ref(false);
const selectActive = ref(false);
const displayItem = ref(null);

const relation = computed(
	() => relationsStore.getRelationsForField(props.collection, props.field)?.[0] ?? null,
);
const relatedCollection = computed(() => relation.value?.related_collection ?? null);
const circularField = computed(() => relation.value?.meta?.one_field ?? undefined);

const relatedPkField = computed(() =>
	relatedCollection.value
		? fieldsStore.getPrimaryKeyFieldForCollection(relatedCollection.value)?.field
		: null,
);

const resolvedTemplate = computed(() => {
	if (props.template) return props.template;
	const meta = relatedCollection.value
		? collectionsStore.getCollection(relatedCollection.value)?.meta
		: null;
	return meta?.display_template || `{{ ${relatedPkField.value ?? 'id'} }}`;
});

const hasValue = computed(() => props.value !== null && props.value !== undefined);

// A staged (unsaved) item arrives as an object; a linked one as a bare primary key.
const stagedEdits = computed(() =>
	props.value && typeof props.value === 'object' ? props.value : {},
);

const editPrimaryKey = computed(() => {
	if (!hasValue.value) return '+';
	if (typeof props.value === 'object') return props.value?.[relatedPkField.value] ?? '+';
	return props.value;
});

const selection = computed(() => {
	if (!hasValue.value || !relatedPkField.value) return [];
	if (typeof props.value === 'object') return [props.value[relatedPkField.value]];
	return [props.value];
});

function itemEndpoint(collection, key) {
	const base = collection.startsWith('directus_')
		? `/${collection.substring(9)}`
		: `/items/${collection}`;
	return `${base}/${encodeURIComponent(key)}`;
}

function templateFields() {
	const found = [...String(resolvedTemplate.value).matchAll(/\{\{([^}]+)\}\}/g)].map((m) =>
		m[1].trim(),
	);
	const fields = new Set(found);
	if (relatedPkField.value) fields.add(relatedPkField.value);
	return [...fields];
}

async function loadDisplayItem() {
	if (!hasValue.value || !relatedCollection.value) {
		displayItem.value = null;
		return;
	}
	// Staged items are not on the server yet — render what is in hand.
	if (typeof props.value === 'object') {
		displayItem.value = props.value;
		return;
	}
	try {
		const response = await api.get(itemEndpoint(relatedCollection.value, props.value), {
			params: { fields: templateFields() },
		});
		displayItem.value = response.data.data;
	} catch {
		displayItem.value = { [relatedPkField.value ?? 'id']: props.value };
	}
}

watch([() => props.value, relatedCollection], loadDisplayItem, { immediate: true });

function onDrawerInput(item) {
	if (props.disabled) return;
	emit('input', item);
}

function onSelect(keys) {
	if (keys && keys[0] !== undefined) emit('input', keys[0]);
	else emit('input', null);
	selectActive.value = false;
}

function deselect() {
	emit('input', null);
}
</script>

<style scoped>
.m2o-buttons {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.selected {
	display: flex;
	align-items: center;
	gap: 8px;
	height: var(--theme--form--field--input--height, 60px);
	padding: var(--theme--form--field--input--padding, 16px);
	background-color: var(--theme--form--field--input--background, var(--background-page));
	border: var(--theme--border-width, 2px) solid
		var(--theme--form--field--input--border-color, var(--border-normal));
	border-radius: var(--theme--border-radius, 6px);
}

.spacer {
	flex-grow: 1;
}

.actions {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}

/* --v-button-width sets inline-size outright; --v-button-min-width is only a
   floor, above which each button still grows to fit its own label. Using width
   is what actually makes "Create New" and "Add Existing" identical.
   Kept in sync with the Custom CSS that sizes the built-in list interfaces. */
.actions :deep(.button) {
	--v-button-width: 10rem !important;
	--v-button-min-width: 0 !important;
}
</style>
