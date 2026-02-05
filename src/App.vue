<template>
	<div id="valtimo-app">
		<NcEmptyContent
			:name="t('valtimo', 'Valtimo')"
			:description="t('valtimo', 'BPM and case management integration for Nextcloud')">
			<template #icon>
				<FileDocumentIcon :size="64" />
			</template>
		</NcEmptyContent>
	</div>
</template>

<script>
import { NcEmptyContent } from '@nextcloud/vue'
import FileDocumentIcon from 'vue-material-design-icons/FileDocument.vue'

export default {
	name: 'App',
	components: {
		NcEmptyContent,
		FileDocumentIcon,
	},
}
</script>
