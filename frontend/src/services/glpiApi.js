import axios from 'axios'

/**
 * Taille max d’ids par POST vers `ajax/native.php` (ticket_counts, plages, groupes).
 * Plusieurs requêtes courtes évitent un seul POST très long → 504 Gateway Time-out (nginx).
 */
const CM_NATIVE_POST_CHUNK = 75

/**
 * Service GLPI : deux transports possibles.
 * - **Développement** : proxy Vite `/api/glpi/...` → FastAPI (jetons côté serveur Python).
 * - **Plugin GLPI** : `ajax/native.php` (PHP, session GLPI, aucun jeton REST).
 */
class GLPIApiService {
  constructor() {
    /** Ancien marqueur de session client — conservé pour compatibilité avec clearCachedSession */
    this.cachedSessionToken = null
    /** ID searchOption pour « Catégorie ITIL » sur Ticket (résolu via listSearchOptions/Ticket) */
    this._ticketCategorySearchFieldId = null
    /** ID searchOption pour un champ date sur Ticket (ouverte / création — pour la chaleur temporelle) */
    this._ticketDateSearchFieldId = null
    /** Groupe assigné au ticket (search/Ticket) — heatmap « clôturés par groupe » */
    this._ticketGroupAssignSearchFieldId = null
    /** Date de résolution (solvedate) — filtre temporel sur clôture */
    this._ticketSolvedateSearchFieldId = null
    /** Statut du ticket (5 résolu, 6 clos typiquement) */
    this._ticketStatusSearchFieldId = null
  }

  /**
   * Indique si le JS tourne dans le plugin GLPI (données via PHP + session).
   */
  _isNativePlugin() {
    return typeof window !== 'undefined' && Boolean(window.__CM_NATIVE_API__)
  }

  /**
   * URL de base du script ajax/native.php (sans slash final).
   */
  _nativeEndpointBase() {
    return String(window.__CM_NATIVE_API__ || '').replace(/\/?$/, '')
  }

  /**
   * Requête GET native : ?action=…
   */
  _nativeGetUrl(action) {
    return `${this._nativeEndpointBase()}?action=${encodeURIComponent(action)}`
  }

  /**
   * POST JSON vers native.php avec jeton CSRF GLPI (réutilisable, validateCSRF preserve).
   */
  _nativePostJson(action, body) {
    const token =
      typeof window !== 'undefined' && window.__CM_GLPI_CSRF_TOKEN__
        ? String(window.__CM_GLPI_CSRF_TOKEN__)
        : ''
    if (!token) {
      return Promise.reject(
        new Error(
          'Jeton CSRF GLPI absent (__CM_GLPI_CSRF_TOKEN__) — rechargez la page du visualiseur depuis GLPI.'
        )
      )
    }
    // GLPI 11 — {@see \Glpi\Kernel\Listener\ControllerListener\CheckCsrfListener} :
    // - Si `Request::isXmlHttpRequest()` est vrai → CSRF lu depuis l’en-tête `X-Glpi-Csrf-Token`.
    // - Sinon → CSRF lu depuis `$request->request` (formulaire), jamais depuis le corps JSON brut.
    // Axios récent n’envoie pas toujours `X-Requested-With`, donc sans le forcer la branche
    // « non-XHR » voit un tableau vide → « L’action que vous avez réalisée n’est pas autorisée ».
    return axios.post(
      `${this._nativeEndpointBase()}?action=${encodeURIComponent(action)}`,
      { ...body, _glpi_csrf_token: token },
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-Glpi-Csrf-Token': token
        }
      }
    )
  }

  /**
   * Vérifie la réponse JSON de `ajax/native.php` ({ ok: true, … }) ou l’erreur standard GLPI / Symfony
   * (`{ error: true, title, message, trace? }` quand une exception n’est pas interceptée côté PHP).
   *
   * @param {{ data?: unknown }} res — réponse Axios
   * @param {string} fallbackMessage — si ni ok ni message structuré
   */
  _assertNativeOk(res, fallbackMessage) {
    const d = res && typeof res === 'object' && 'data' in res ? res.data : null
    if (d && typeof d === 'object' && d.error === true) {
      const t = typeof d.title === 'string' && d.title.trim() !== '' ? d.title.trim() : 'Erreur GLPI'
      const m = typeof d.message === 'string' && d.message.trim() !== '' ? d.message.trim() : ''
      throw new Error(m ? `${t} — ${m}` : t)
    }
    if (!d || typeof d !== 'object' || !d.ok) {
      const errText =
        typeof d?.error === 'string' && d.error.trim() !== '' ? d.error.trim() : fallbackMessage
      throw new Error(errText)
    }
  }

  /**
   * Découpe une liste d’ids strictement positifs en lots (ordre conservé, sans doublons).
   * @param {number[]} ids
   * @param {number} size
   * @returns {number[][]}
   */
  _nativeChunkPositiveIds(ids, size) {
    const list = [
      ...new Set(
        (ids || []).map((x) => Number(x)).filter((n) => Number.isFinite(n) && n > 0)
      )
    ]
    const chunks = []
    for (let i = 0; i < list.length; i += size) {
      chunks.push(list.slice(i, i + size))
    }
    return chunks
  }

  /**
   * Réinitialise la session en mémoire (ex. après déconnexion)
   */
  clearCachedSession() {
    this.cachedSessionToken = null
    this._ticketCategorySearchFieldId = null
    this._ticketDateSearchFieldId = null
    this._ticketGroupAssignSearchFieldId = null
    this._ticketSolvedateSearchFieldId = null
    this._ticketStatusSearchFieldId = null
  }

  /**
   * Préfixe des appels « API bas niveau » (mode FastAPI / proxy REST uniquement).
   *
   * @returns {string} URL de base (avec slash final)
   */
  _lowLevelBaseUrl() {
    return '/api/glpi/'
  }

  async _getWithProxyFallback(pathRelativeToApirest, headers) {
    const url = `${this._lowLevelBaseUrl()}${pathRelativeToApirest}`
    return await axios.get(url, { headers })
  }

  async _postWithProxyFallback(pathRelativeToApirest, body, headers) {
    const url = `${this._lowLevelBaseUrl()}${pathRelativeToApirest}`
    return await axios.post(url, body, { headers })
  }

  /**
   * Réchauffe la session côté serveur (optionnel). Les en-têtes GLPI sont ajoutés par le backend.
   */
  async initLowLevelSession() {
    if (this._isNativePlugin()) {
      return ''
    }
    if (this.cachedSessionToken) {
      return this.cachedSessionToken
    }
    const apiUrl = this._lowLevelBaseUrl()
    const response = await axios.get(`${apiUrl}initSession`, {
      headers: { 'Content-Type': 'application/json' }
    })
    const sessionToken = response.data.session_token
    if (!sessionToken) {
      throw new Error('session_token absent dans la réponse initSession')
    }
    this.cachedSessionToken = sessionToken
    return sessionToken
  }

  /**
   * Headers côté client : le backend injecte App-Token, User-Token et Session-Token vers GLPI.
   */
  async _sessionHeaders() {
    return {
      'Content-Type': 'application/json'
    }
  }

  /**
   * Infos utilisateur / session courante via getFullSession (API bas niveau)
   * @returns {Promise<Object>} Objet normalisé pour l’UI (username, id, etc.)
   */
  async getUserInfo() {
    const headers = await this._sessionHeaders()
    const res = await this._getWithProxyFallback('getFullSession', headers)
    const session = res.data.session || res.data
    const glpiID = session.glpiID ?? session.id
    const username = session.glpi_username ?? session.name ?? ''
    return {
      id: glpiID,
      username,
      name: username,
      realname: session.glpi_realname ?? session.realname,
      firstname: session.glpi_firstname ?? session.firstname,
      email: session.glpi_email ?? session.email,
      session
    }
  }

  /**
   * Liste des catégories ITIL (même logique métier qu’avant, sans dépendance à l’API haut niveau)
   */
  async getITILCategories() {
    return this.getITILCategoriesLowLevel()
  }

  /**
   * Récupère les catégories ITIL via ITILCategory (ou itilcategory)
   */
  async getITILCategoriesLowLevel() {
    if (this._isNativePlugin()) {
      const res = await axios.get(this._nativeGetUrl('categories'))
      this._assertNativeOk(res, 'Réponse « categories » invalide')
      const categories = Array.isArray(res.data.categories) ? res.data.categories : []
      console.log(`[glpiApi] ${categories.length} catégorie(s) ITIL (PHP natif / session GLPI)`)
      return categories
    }

    const apiUrl = this._lowLevelBaseUrl()
    const headers = await this._sessionHeaders()

    try {
      await this._postWithProxyFallback('changeActiveProfile?profiles_id=4', null, headers)
      console.log('changeActiveProfile: OK ou ignoré')
    } catch (profileError) {
      console.warn('changeActiveProfile non critique:', profileError.response?.status || profileError.message)
    }

    const endpointsToTry = [
      'ITILCategory?range=0-700',
      'itilcategory?range=0-700',
      'ITILCategory',
      'itilcategory'
    ]

    let response = null
    let lastError = null

    const tryRequest = async (endpoint) => {
      try {
        const res = await axios.get(`${apiUrl}${endpoint}`, { headers })
        return { ok: true, res }
      } catch (error) {
        return { ok: false, error, status: error.response?.status }
      }
    }

    for (const endpoint of endpointsToTry) {
      const result = await tryRequest(endpoint)
      if (result.ok) {
        response = result.res
        console.log(`[glpiApi] ITILCategory : réponse OK avec l’endpoint « ${endpoint} »`)
        break
      }
      console.warn(
        `[glpiApi] ITILCategory : échec « ${endpoint} » —`,
        result.status ?? result.error?.message ?? 'erreur'
      )
      lastError = result.error
    }

    if (!response) {
      throw lastError || new Error('Aucun endpoint ITILCategory ne répond')
    }

    let categories = []
    if (Array.isArray(response.data)) {
      categories = response.data
    } else if (response.data && typeof response.data === 'object') {
      const keys = Object.keys(response.data)
      if (keys.length > 0 && keys.every(k => /^\d+$/.test(k))) {
        categories = Object.values(response.data)
      } else {
        categories = [response.data]
      }
    }

    console.log(
      `[glpiApi] ${categories.length} catégorie(s) ITIL parsée(s) depuis la réponse (API bas niveau)`
    )
    return categories
  }

  /**
   * GET search/Ticket avec critères (API documentée en GET pour search/:itemtype)
   */
  async _getSearchTicket(headers, fieldId, categoryId) {
    const apiUrl = this._lowLevelBaseUrl()
    const path = 'search/Ticket'
    const params = {
      'criteria[0][field]': fieldId,
      'criteria[0][searchtype]': 'equals',
      'criteria[0][value]': categoryId,
      range: '0-0'
    }
    const url = `${apiUrl}${path}`
    return await axios.get(url, { headers, params })
  }

  /**
   * search/Ticket : catégorie + plage de dates (ouverte du ticket entre [start, end[).
   * Utilise morethan / lessthan sur le même champ date (convention GLPI search).
   *
   * @param {string} startStr — ex. « 2025-01-01 00:00:00 »
   * @param {string} endStr — exclusif, ex. « 2025-02-01 00:00:00 »
   */
  async _getSearchTicketCategoryDateRange(
    headers,
    categoryFieldId,
    categoryId,
    dateFieldId,
    startStr,
    endStr
  ) {
    const apiUrl = this._lowLevelBaseUrl()
    const path = 'search/Ticket'
    const params = {
      'criteria[0][field]': categoryFieldId,
      'criteria[0][searchtype]': 'equals',
      'criteria[0][value]': categoryId,
      'criteria[1][link]': 'AND',
      'criteria[1][field]': dateFieldId,
      'criteria[1][searchtype]': 'morethan',
      'criteria[1][value]': startStr,
      'criteria[2][link]': 'AND',
      'criteria[2][field]': dateFieldId,
      'criteria[2][searchtype]': 'lessthan',
      'criteria[2][value]': endStr,
      range: '0-0'
    }
    const url = `${apiUrl}${path}`
    return await axios.get(url, { headers, params })
  }

  /** Extrait le nombre de résultats depuis la réponse search */
  _parseSearchTotalCount(res) {
    const payload = res.data
    if (payload == null) return 0
    if (typeof payload.totalcount === 'number') return payload.totalcount
    if (typeof payload.count === 'number') return payload.count
    if (Array.isArray(payload.data)) return payload.data.length
    if (payload.data && typeof payload.data === 'object') return Object.keys(payload.data).length
    return 0
  }

  /**
   * Trouve l’ID de critère de recherche GLPI pour le champ itilcategories_id sur Ticket.
   * @see https://github.com/glpi-project/glpi/blob/main/apirest.md (listSearchOptions / search)
   * @returns {Promise<number>}
   */
  async getTicketItilCategorySearchFieldId() {
    if (this._ticketCategorySearchFieldId != null) {
      return this._ticketCategorySearchFieldId
    }

    const headers = await this._sessionHeaders()
    const res = await this._getWithProxyFallback('listSearchOptions/Ticket', headers)
    const raw = res.data

    const visit = (obj) => {
      if (!obj || typeof obj !== 'object') return null
      for (const key of Object.keys(obj)) {
        const opt = obj[key]
        if (!opt || typeof opt !== 'object') continue
        const field = opt.field
        const linkfield = opt.linkfield
        const uid = opt.uid
        if (field === 'itilcategories_id' || linkfield === 'itilcategories_id') {
          const idNum = Number.parseInt(String(key), 10)
          return Number.isNaN(idNum) ? key : idNum
        }
        if (typeof uid === 'string' && uid.includes('itilcategories_id')) {
          const idNum = Number.parseInt(String(key), 10)
          return Number.isNaN(idNum) ? key : idNum
        }
      }
      return null
    }

    let found = visit(raw)
    if (!found && raw && typeof raw === 'object') {
      for (const section of Object.values(raw)) {
        if (section && typeof section === 'object' && !Array.isArray(section)) {
          found = visit(section)
          if (found != null) break
        }
      }
    }

    if (found == null) {
      console.warn(
        '[glpiApi] listSearchOptions/Ticket : itilcategories_id introuvable — fallback champ 7 (souvent « Catégorie » sur Ticket)'
      )
      found = 7
    }

    this._ticketCategorySearchFieldId = found
    return found
  }

  /**
   * Trouve un champ date pertinent sur Ticket (date d’ouverture ou date de création).
   * Nécessaire pour filtrer les tickets par mois (carte de chaleur temporelle).
   *
   * @returns {Promise<number|string>}
   */
  async getTicketDateSearchFieldId() {
    if (this._ticketDateSearchFieldId != null) {
      return this._ticketDateSearchFieldId
    }

    const headers = await this._sessionHeaders()
    const res = await this._getWithProxyFallback('listSearchOptions/Ticket', headers)
    const raw = res.data

    /** Parcourt listSearchOptions (structure parfois imbriquée) pour lister les champs. */
    const collectOptions = (obj, out = [], depth = 0) => {
      if (!obj || typeof obj !== 'object' || depth > 5) return out
      for (const key of Object.keys(obj)) {
        const opt = obj[key]
        if (opt && typeof opt === 'object' && !Array.isArray(opt)) {
          if (opt.field != null) {
            const idNum = Number.parseInt(String(key), 10)
            out.push({
              key,
              id: Number.isNaN(idNum) ? key : idNum,
              field: opt.field,
              name: opt.name,
              uid: opt.uid
            })
          }
          collectOptions(opt, out, depth + 1)
        }
      }
      return out
    }

    const flat = collectOptions(raw)

    const preferFields = ['date', 'date_creation']
    for (const fname of preferFields) {
      const hit = flat.find((o) => o.field === fname)
      if (hit) {
        this._ticketDateSearchFieldId = hit.id
        console.log(`[glpiApi] Champ date Ticket pour la chaleur temporelle : ${fname} → id ${hit.id}`)
        return this._ticketDateSearchFieldId
      }
    }

    const fallback = flat.find(
      (o) =>
        typeof o.field === 'string' &&
        (o.field.includes('date') || o.field === 'time_to_resolve')
    )
    if (fallback) {
      this._ticketDateSearchFieldId = fallback.id
      console.warn(
        `[glpiApi] Champ date Ticket (fallback) : field « ${fallback.field} » → id ${fallback.id}`
      )
      return this._ticketDateSearchFieldId
    }

    console.warn('[glpiApi] Aucun champ date Ticket trouvé — fallback id 12 (souvent « Date » sur Ticket)')
    this._ticketDateSearchFieldId = 12
    return this._ticketDateSearchFieldId
  }

  /**
   * Nombre de tickets dont la catégorie ITIL est exactement categoryId (search GLPI).
   * @param {number} categoryId
   * @param {number} [fieldId] — évite de relire listSearchOptions si déjà connu
   * @returns {Promise<number>}
   */
  async getTicketCountByCategory(categoryId, fieldId = null) {
    const fid = fieldId != null ? fieldId : await this.getTicketItilCategorySearchFieldId()
    const headers = await this._sessionHeaders()
    try {
      const res = await this._getSearchTicket(headers, fid, categoryId)
      return this._parseSearchTotalCount(res)
    } catch (e) {
      console.warn(`[glpiApi] search/Ticket catégorie ${categoryId}:`, e.response?.status, e.response?.data || e.message)
      return 0
    }
  }

  /**
   * Compteurs pour plusieurs catégories (requêtes en parallèle par paquets pour ne pas saturer GLPI).
   * @param {number[]} categoryIds
   * @param {{ concurrency?: number, onProgress?: (done: number, total: number) => void }} [opts]
   *   — `onProgress` appelé après chaque lot (done = nombre de catégories déjà traitées, total = taille liste).
   * @returns {Promise<Record<number, number>>}
   */
  async getTicketCountsForCategories(categoryIds, opts = {}) {
    const concurrency = opts.concurrency ?? 8
    const onProgress = typeof opts.onProgress === 'function' ? opts.onProgress : null
    const total = categoryIds.length

    if (this._isNativePlugin()) {
      const counts = {}
      for (const id of categoryIds) {
        const n = Number(id)
        if (Number.isFinite(n)) {
          counts[n] = 0
        }
      }
      if (total === 0) {
        return counts
      }
      onProgress?.(0, total)
      const chunks = this._nativeChunkPositiveIds(categoryIds, CM_NATIVE_POST_CHUNK)
      let done = 0
      for (const chunk of chunks) {
        const res = await this._nativePostJson('ticket_counts', { ids: chunk })
        this._assertNativeOk(res, 'ticket_counts')
        const partial = res.data?.counts
        if (partial && typeof partial === 'object') {
          for (const [k, v] of Object.entries(partial)) {
            const id = Number.parseInt(String(k), 10)
            if (Number.isFinite(id)) {
              counts[id] = Number(v) || 0
            }
          }
        }
        done += chunk.length
        onProgress?.(Math.min(done, total), total)
      }
      onProgress?.(total, total)
      return counts
    }

    console.log(
      `[glpiApi] Comptage tickets : ${total} catégorie(s), lots de ${concurrency} requête(s) max en parallèle`
    )

    const fieldId = await this.getTicketItilCategorySearchFieldId()
    console.log(`[glpiApi] Champ search/Ticket pour itilcategories_id : ${fieldId}`)

    const headers = await this._sessionHeaders()

    const counts = {}
    categoryIds.forEach((id) => {
      counts[id] = 0
    })

    const runOne = async (id) => {
      try {
        const res = await this._getSearchTicket(headers, fieldId, id)
        counts[id] = this._parseSearchTotalCount(res)
      } catch (e) {
        console.warn(`[glpiApi] ticket count cat ${id}:`, e.response?.status || e.message)
        counts[id] = 0
      }
    }

    let done = 0
    if (onProgress && total > 0) {
      onProgress(0, total)
    }

    for (let i = 0; i < categoryIds.length; i += concurrency) {
      const batch = categoryIds.slice(i, i + concurrency)
      await Promise.all(batch.map((id) => runOne(id)))
      done += batch.length
      if (onProgress) {
        onProgress(done, total)
      }
    }

    console.log(`[glpiApi] Comptage tickets terminé : ${total} catégorie(s) agrégée(s)`)
    return counts
  }

  /**
   * Compteurs par catégorie pour une plage de dates (tickets dont la date du champ retenu est dans [start, end[).
   * Même parallélisation que {@link getTicketCountsForCategories}.
   *
   * @param {number[]} categoryIds
   * @param {string} startStr — « YYYY-MM-DD HH:mm:ss » (début inclus)
   * @param {string} endStr — fin exclusive
   * @param {{ concurrency?: number, onProgress?: (done: number, total: number) => void }} [opts]
   * @returns {Promise<Record<number, number>>}
   */
  async getTicketCountsForCategoriesInDateRange(categoryIds, startStr, endStr, opts = {}) {
    const concurrency = opts.concurrency ?? 6
    const onProgress = typeof opts.onProgress === 'function' ? opts.onProgress : null
    const total = categoryIds.length

    if (this._isNativePlugin()) {
      const counts = {}
      for (const id of categoryIds) {
        const n = Number(id)
        if (Number.isFinite(n)) {
          counts[n] = 0
        }
      }
      if (total === 0) {
        return counts
      }
      onProgress?.(0, total)
      const chunks = this._nativeChunkPositiveIds(categoryIds, CM_NATIVE_POST_CHUNK)
      let done = 0
      for (const chunk of chunks) {
        const res = await this._nativePostJson('ticket_counts_range', {
          ids: chunk,
          start: startStr,
          end: endStr
        })
        this._assertNativeOk(res, 'ticket_counts_range')
        const partial = res.data?.counts
        if (partial && typeof partial === 'object') {
          for (const [k, v] of Object.entries(partial)) {
            const id = Number.parseInt(String(k), 10)
            if (Number.isFinite(id)) {
              counts[id] = Number(v) || 0
            }
          }
        }
        done += chunk.length
        onProgress?.(Math.min(done, total), total)
      }
      onProgress?.(total, total)
      return counts
    }

    const categoryFieldId = await this.getTicketItilCategorySearchFieldId()
    const dateFieldId = await this.getTicketDateSearchFieldId()
    const headers = await this._sessionHeaders()

    const counts = {}
    categoryIds.forEach((id) => {
      counts[id] = 0
    })

    const runOne = async (id) => {
      try {
        const res = await this._getSearchTicketCategoryDateRange(
          headers,
          categoryFieldId,
          id,
          dateFieldId,
          startStr,
          endStr
        )
        counts[id] = this._parseSearchTotalCount(res)
      } catch (e) {
        console.warn(`[glpiApi] ticket count cat ${id} (plage date):`, e.response?.status || e.message)
        counts[id] = 0
      }
    }

    let done = 0
    if (onProgress && total > 0) {
      onProgress(0, total)
    }

    for (let i = 0; i < categoryIds.length; i += concurrency) {
      const batch = categoryIds.slice(i, i + concurrency)
      await Promise.all(batch.map((id) => runOne(id)))
      done += batch.length
      if (onProgress) {
        onProgress(done, total)
      }
    }

    return counts
  }

  /**
   * Aplatit listSearchOptions/Ticket pour recherche d’ids de champs (même logique que getTicketDateSearchFieldId).
   * @private
   */
  _collectTicketSearchOptionsFlat(raw) {
    const out = []
    const walk = (obj, depth) => {
      if (!obj || typeof obj !== 'object' || depth > 5) return
      for (const key of Object.keys(obj)) {
        const opt = obj[key]
        if (opt && typeof opt === 'object' && !Array.isArray(opt)) {
          if (opt.field != null) {
            const idNum = Number.parseInt(String(key), 10)
            out.push({
              key,
              id: Number.isNaN(idNum) ? key : idNum,
              field: opt.field,
              linkfield: opt.linkfield,
              name: opt.name,
              uid: opt.uid
            })
          }
          walk(opt, depth + 1)
        }
      }
    }
    walk(raw, 0)
    return out
  }

  /**
   * Champ search pour le groupe assigné au ticket (groups_id_assign).
   * @returns {Promise<number|string>}
   */
  async getTicketGroupsAssignSearchFieldId() {
    if (this._ticketGroupAssignSearchFieldId != null) {
      return this._ticketGroupAssignSearchFieldId
    }
    const headers = await this._sessionHeaders()
    const res = await this._getWithProxyFallback('listSearchOptions/Ticket', headers)
    const flat = this._collectTicketSearchOptionsFlat(res.data)
    const hit = flat.find(
      (o) =>
        o.linkfield === 'groups_id_assign' ||
        o.field === 'groups_id_assign' ||
        (typeof o.uid === 'string' && o.uid.includes('groups_id_assign'))
    )
    if (hit) {
      this._ticketGroupAssignSearchFieldId = hit.id
      console.log(`[glpiApi] Champ groupe assigné Ticket : ${hit.field || hit.linkfield} → id ${hit.id}`)
      return this._ticketGroupAssignSearchFieldId
    }
    const nameHit = flat.find(
      (o) =>
        typeof o.name === 'string' &&
        /assign/i.test(o.name) &&
        (/group|groupe/i.test(o.name) || /technician|technicien/i.test(o.name))
    )
    if (nameHit) {
      this._ticketGroupAssignSearchFieldId = nameHit.id
      console.warn(`[glpiApi] Groupe assigné (heuristique nom) → id ${nameHit.id}`)
      return this._ticketGroupAssignSearchFieldId
    }
    console.warn('[glpiApi] groups_id_assign introuvable — fallback id 8 (souvent « Groupe » assigné)')
    this._ticketGroupAssignSearchFieldId = 8
    return this._ticketGroupAssignSearchFieldId
  }

  /**
   * Champ date de résolution (solvedate) pour filtrer les clôtures par mois.
   * @returns {Promise<number|string>}
   */
  async getTicketSolvedateSearchFieldId() {
    if (this._ticketSolvedateSearchFieldId != null) {
      return this._ticketSolvedateSearchFieldId
    }
    const headers = await this._sessionHeaders()
    const res = await this._getWithProxyFallback('listSearchOptions/Ticket', headers)
    const flat = this._collectTicketSearchOptionsFlat(res.data)
    const hit = flat.find(
      (o) => o.field === 'solvedate' || o.linkfield === 'solvedate' || (o.uid && String(o.uid).includes('solvedate'))
    )
    if (hit) {
      this._ticketSolvedateSearchFieldId = hit.id
      console.log(`[glpiApi] Champ solvedate Ticket → id ${hit.id}`)
      return this._ticketSolvedateSearchFieldId
    }
    console.warn('[glpiApi] solvedate introuvable — fallback id 18 (souvent « Date de résolution »)')
    this._ticketSolvedateSearchFieldId = 18
    return this._ticketSolvedateSearchFieldId
  }

  /**
   * Champ statut Ticket (equals 5 = résolu, 6 = clos en GLPI standard).
   * @returns {Promise<number|string>}
   */
  async getTicketStatusSearchFieldId() {
    if (this._ticketStatusSearchFieldId != null) {
      return this._ticketStatusSearchFieldId
    }
    const headers = await this._sessionHeaders()
    const res = await this._getWithProxyFallback('listSearchOptions/Ticket', headers)
    const flat = this._collectTicketSearchOptionsFlat(res.data)
    const hit = flat.find(
      (o) =>
        o.field === 'status' ||
        o.linkfield === 'status' ||
        (typeof o.uid === 'string' && o.uid.includes('status') && !String(o.uid).includes('sub'))
    )
    if (hit) {
      this._ticketStatusSearchFieldId = hit.id
      console.log(`[glpiApi] Champ statut Ticket → id ${hit.id}`)
      return this._ticketStatusSearchFieldId
    }
    console.warn('[glpiApi] status introuvable — fallback id 12')
    this._ticketStatusSearchFieldId = 12
    return this._ticketStatusSearchFieldId
  }

  /**
   * search/Ticket : groupe assigné + plage solvedate + statut exact.
   */
  async _getSearchTicketGroupStatusDateRange(
    headers,
    groupFieldId,
    groupId,
    dateFieldId,
    startStr,
    endStr,
    statusFieldId,
    statusValue
  ) {
    const apiUrl = this._lowLevelBaseUrl()
    const path = 'search/Ticket'
    const params = {
      'criteria[0][field]': groupFieldId,
      'criteria[0][searchtype]': 'equals',
      'criteria[0][value]': groupId,
      'criteria[1][link]': 'AND',
      'criteria[1][field]': dateFieldId,
      'criteria[1][searchtype]': 'morethan',
      'criteria[1][value]': startStr,
      'criteria[2][link]': 'AND',
      'criteria[2][field]': dateFieldId,
      'criteria[2][searchtype]': 'lessthan',
      'criteria[2][value]': endStr,
      'criteria[3][link]': 'AND',
      'criteria[3][field]': statusFieldId,
      'criteria[3][searchtype]': 'equals',
      'criteria[3][value]': statusValue,
      range: '0-0'
    }
    const url = `${apiUrl}${path}`
    return await axios.get(url, { headers, params })
  }

  /**
   * Compte les tickets par groupe pour une plage [start, end[ : statut résolu (5) + clos (6),
   * date de résolution (solvedate) dans la plage, groupe assigné = groupId.
   *
   * @param {number[]} groupIds
   * @param {string} startStr
   * @param {string} endStr
   * @param {{ concurrency?: number, onProgress?: (done: number, total: number) => void }} [opts]
   * @returns {Promise<Record<number, number>>}
   */
  async getTicketSolvedOrClosedCountsForGroupsInDateRange(groupIds, startStr, endStr, opts = {}) {
    const concurrency = opts.concurrency ?? 6
    const onProgress = typeof opts.onProgress === 'function' ? opts.onProgress : null
    const total = groupIds.length

    if (this._isNativePlugin()) {
      const counts = {}
      for (const id of groupIds) {
        const n = Number(id)
        if (Number.isFinite(n)) {
          counts[n] = 0
        }
      }
      if (total === 0) {
        return counts
      }
      onProgress?.(0, total)
      const chunks = this._nativeChunkPositiveIds(groupIds, CM_NATIVE_POST_CHUNK)
      let done = 0
      for (const chunk of chunks) {
        const res = await this._nativePostJson('group_counts_range', {
          group_ids: chunk,
          start: startStr,
          end: endStr
        })
        this._assertNativeOk(res, 'group_counts_range')
        const partial = res.data?.counts
        if (partial && typeof partial === 'object') {
          for (const [k, v] of Object.entries(partial)) {
            const id = Number.parseInt(String(k), 10)
            if (Number.isFinite(id)) {
              counts[id] = Number(v) || 0
            }
          }
        }
        done += chunk.length
        onProgress?.(Math.min(done, total), total)
      }
      onProgress?.(total, total)
      return counts
    }

    const headers = await this._sessionHeaders()
    const groupFieldId = await this.getTicketGroupsAssignSearchFieldId()
    const dateFieldId = await this.getTicketSolvedateSearchFieldId()
    const statusFieldId = await this.getTicketStatusSearchFieldId()
    /** Statuts GLPI classiques : résolu + clos (un ticket n’a qu’un statut à la fois — somme disjointe). */
    const statusValues = [5, 6]

    const counts = {}
    groupIds.forEach((id) => {
      counts[id] = 0
    })

    const runOne = async (gid) => {
      let sum = 0
      for (const st of statusValues) {
        try {
          const res = await this._getSearchTicketGroupStatusDateRange(
            headers,
            groupFieldId,
            gid,
            dateFieldId,
            startStr,
            endStr,
            statusFieldId,
            st
          )
          sum += this._parseSearchTotalCount(res)
        } catch (e) {
          console.warn(`[glpiApi] comptage groupe ${gid} statut ${st}:`, e.response?.status || e.message)
        }
      }
      counts[gid] = sum
    }

    let done = 0
    if (onProgress && total > 0) {
      onProgress(0, total)
    }

    for (let i = 0; i < groupIds.length; i += concurrency) {
      const batch = groupIds.slice(i, i + concurrency)
      await Promise.all(batch.map((id) => runOne(id)))
      done += batch.length
      if (onProgress) {
        onProgress(done, total)
      }
    }

    return counts
  }

  /**
   * Liste des groupes GLPI (id + nom) pour l’axe des lignes de la heatmap groupes.
   * @returns {Promise<Array<{ id: number, name: string }>>}
   */
  async getGroups() {
    if (this._isNativePlugin()) {
      const res = await axios.get(this._nativeGetUrl('groups'))
      this._assertNativeOk(res, 'groups')
      const rows = Array.isArray(res.data.groups) ? res.data.groups : []
      console.log(`[glpiApi] ${rows.length} groupe(s) (PHP natif)`)
      return rows
        .map((g) => ({
          id: Number(g.id),
          name: (g.name || '').trim() || `Groupe ${g.id}`
        }))
        .filter((g) => Number.isFinite(g.id) && g.id > 0)
    }

    const apiUrl = this._lowLevelBaseUrl()
    const headers = await this._sessionHeaders()

    const endpointsToTry = ['Group?range=0-8000', 'group?range=0-8000', 'Group', 'group']

    let response = null
    let lastError = null

    const tryRequest = async (endpoint) => {
      try {
        const res = await axios.get(`${apiUrl}${endpoint}`, { headers })
        return { ok: true, res }
      } catch (error) {
        return { ok: false, error, status: error.response?.status }
      }
    }

    for (const endpoint of endpointsToTry) {
      const result = await tryRequest(endpoint)
      if (result.ok) {
        response = result.res
        console.log(`[glpiApi] Group : OK avec « ${endpoint} »`)
        break
      }
      lastError = result.error
    }

    if (!response) {
      throw lastError || new Error('Aucun endpoint Group ne répond')
    }

    let rows = []
    if (Array.isArray(response.data)) {
      rows = response.data
    } else if (response.data && typeof response.data === 'object') {
      const keys = Object.keys(response.data)
      if (keys.length > 0 && keys.every((k) => /^\d+$/.test(k))) {
        rows = Object.values(response.data)
      }
    }

    const out = rows.map((g) => {
      const id = Number(g.id)
      const name = (g.completename || g.name || '').trim() || `Groupe ${g.id}`
      return { id, name }
    }).filter((g) => Number.isFinite(g.id) && g.id > 0)

    console.log(`[glpiApi] ${out.length} groupe(s) chargé(s)`)
    return out
  }
}

export default new GLPIApiService()
