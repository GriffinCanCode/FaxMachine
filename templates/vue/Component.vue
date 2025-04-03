<template>
  <div class="component">
    <h2>{{ title }}</h2>
    <div v-if="loading" class="loading">
      Loading...
    </div>
    <div v-else-if="error" class="error">
      {{ error }}
    </div>
    <div v-else class="content">
      <!-- Content goes here -->
      <slot></slot>
      <button @click="handleClick">{{ buttonText }}</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ComponentName',
  
  props: {
    /**
     * The title of the component
     */
    title: {
      type: String,
      required: true,
    },
    /**
     * Text for the button
     */
    buttonText: {
      type: String,
      default: 'Click me',
    },
  },
  
  data() {
    return {
      loading: false,
      error: null,
      data: null,
    };
  },
  
  computed: {
    /**
     * Computed property example
     */
    computedValue() {
      return this.data ? this.data.value : '';
    },
  },
  
  watch: {
    /**
     * Watch for changes in props
     */
    title(newVal, oldVal) {
      console.log(`Title changed from ${oldVal} to ${newVal}`);
    },
  },
  
  created() {
    // Called when the component is created
    this.fetchData();
  },
  
  mounted() {
    // Called when the component is mounted to the DOM
    console.log('Component mounted');
  },
  
  methods: {
    /**
     * Handle button click
     */
    handleClick() {
      this.$emit('click', { timestamp: Date.now() });
    },
    
    /**
     * Fetch data from API
     */
    async fetchData() {
      this.loading = true;
      this.error = null;
      
      try {
        // Example API call
        // const response = await api.getData();
        // this.data = response.data;
        this.data = { value: 'Example data' };
      } catch (err) {
        this.error = 'Failed to load data';
        console.error(err);
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.component {
  padding: 1rem;
  border-radius: 0.5rem;
  background-color: #f8f9fa;
}

.loading {
  color: #6c757d;
  font-style: italic;
}

.error {
  color: #dc3545;
  font-weight: bold;
}

.content {
  margin-top: 1rem;
}

button {
  padding: 0.5rem 1rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
}

button:hover {
  background-color: #0069d9;
}
</style> 