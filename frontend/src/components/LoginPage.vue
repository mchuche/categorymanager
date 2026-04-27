<template>
  <div class="login-container">
    <div class="login-theme-bar">
      <ThemeToggle />
    </div>
    <div class="login-card">
      <h1 class="login-title">CategorieManager</h1>
      <p class="login-subtitle">Visualiseur de catégories GLPI (API REST bas niveau)</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="glpi-url">URL GLPI</label>
          <input
            id="glpi-url"
            v-model="formData.glpiUrl"
            type="text"
            placeholder="https://votre-instance.glpi.fr"
            required
            class="form-input"
          />
          <small class="form-help">URL de base de votre instance (sans /apirest.php)</small>
        </div>

        <div class="form-group">
          <label for="app-token">App-Token</label>
          <input
            id="app-token"
            v-model="formData.appToken"
            type="text"
            placeholder="Token d’application"
            required
            class="form-input"
          />
          <small class="form-help">Configuration &gt; API &gt; jetons d’API (apirest.php)</small>
        </div>

        <div class="form-group">
          <label for="user-token">User-Token</label>
          <input
            id="user-token"
            v-model="formData.userToken"
            type="password"
            placeholder="Token utilisateur"
            required
            class="form-input"
          />
          <small class="form-help">Profil utilisateur &gt; paramètres &gt; jeton d’accès distant</small>
        </div>

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <button type="submit" :disabled="isLoading" class="login-button">
          <span v-if="isLoading">Connexion…</span>
          <span v-else>Se connecter</span>
        </button>

        <div class="dev-info">
          <small>Les identifiants sont enregistrés dans la session du navigateur (sessionStorage).</small>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { readJsonSession, writeJsonSession } from '../services/browserLocalCache'
import {
  useAuthStore,
  GLPI_AUTH_SESSION_KEY,
  GLPI_CONNECTION_PARAMS_SESSION_KEY
} from '../stores/auth'
import ThemeToggle from './ThemeToggle.vue'

const emit = defineEmits(['authenticated'])
const authStore = useAuthStore()

const formData = ref({
  glpiUrl: '',
  appToken: '',
  userToken: ''
})

const isLoading = ref(false)
const errorMessage = ref('')

/**
 * Pré-remplit le formulaire : d’abord la sauvegarde « brouillon » connexion, sinon l’auth déjà en session.
 */
function loadConnectionParams() {
  const draft = readJsonSession(GLPI_CONNECTION_PARAMS_SESSION_KEY)
  if (draft && typeof draft === 'object') {
    formData.value.glpiUrl = draft.glpiUrl || ''
    formData.value.appToken = draft.appToken || ''
    formData.value.userToken = draft.userToken || ''
    return
  }
  const authData = readJsonSession(GLPI_AUTH_SESSION_KEY)
  if (authData && typeof authData === 'object') {
    formData.value.glpiUrl = authData.glpiUrl || ''
    formData.value.appToken = authData.appToken || ''
    formData.value.userToken = authData.userToken || ''
  }
}

function saveConnectionParams() {
  writeJsonSession(
    GLPI_CONNECTION_PARAMS_SESSION_KEY,
    {
      glpiUrl: formData.value.glpiUrl,
      appToken: formData.value.appToken,
      userToken: formData.value.userToken
    },
    { logLabel: 'glpi_connection_params' }
  )
}

onMounted(() => {
  loadConnectionParams()
})

/**
 * Connexion : enregistre URL + App-Token + User-Token, puis notifie l’app
 */
function handleLogin() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    saveConnectionParams()
    authStore.setAuth(
      formData.value.glpiUrl.trim(),
      formData.value.appToken.trim(),
      formData.value.userToken.trim()
    )
    emit('authenticated')
  } catch (error) {
    console.error(error)
    errorMessage.value = error.message || 'Connexion impossible'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
/* Barre fixe : bascule thème sans dépendre de la carte (dégradé derrière) */
.login-theme-bar {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 20;
}

.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(
    135deg,
    var(--app-login-gradient-start) 0%,
    var(--app-login-gradient-end) 100%
  );
  padding: 20px;
}

.login-card {
  background: var(--app-surface);
  border-radius: 12px;
  box-shadow: 0 10px 40px var(--app-card-shadow);
  padding: 40px;
  width: 100%;
  max-width: 500px;
}

.login-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--app-text);
  text-align: center;
  margin-bottom: 8px;
}

.login-subtitle {
  text-align: center;
  color: var(--app-text-muted);
  margin-bottom: 32px;
  font-size: 0.95rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 600;
  color: var(--app-text);
  font-size: 0.9rem;
}

.form-input {
  padding: 12px;
  border: 2px solid var(--app-input-border);
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
  background: var(--app-input-bg);
  color: var(--app-text);
}

.form-input:focus {
  outline: none;
  border-color: var(--app-primary);
}

.form-help {
  color: var(--app-text-soft);
  font-size: 0.85rem;
  margin-top: -4px;
}

.error-message {
  background-color: var(--app-error-bg);
  color: var(--app-error-text);
  padding: 12px;
  border-radius: 8px;
  font-size: 0.9rem;
  border: 1px solid var(--app-error-border);
}

.login-button {
  background: linear-gradient(
    135deg,
    var(--app-login-gradient-start) 0%,
    var(--app-login-gradient-end) 100%
  );
  color: #ffffff;
  border: none;
  padding: 14px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  margin-top: 8px;
}

.login-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--app-login-btn-shadow);
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dev-info {
  margin-top: 16px;
  text-align: center;
  padding: 8px;
  background-color: var(--app-dev-info-bg);
  border-radius: 6px;
}

.dev-info small {
  color: var(--app-text-muted);
  font-size: 0.85rem;
}
</style>
