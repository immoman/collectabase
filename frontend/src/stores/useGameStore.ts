import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { gamesApi, platformsApi } from '../api'
import type { Game, Platform } from '../types'

export const useGameStore = defineStore('games', () => {
  // ── State ──────────────────────────────────────────────────
  const games = ref<Game[]>([])
  const platforms = ref<Platform[]>([])
  const loading = ref<boolean>(false)
  const loaded = ref<boolean>(false)
  const error = ref<unknown>(null)

  // ── Getters ────────────────────────────────────────────────
  const collection = computed<Game[]>(() => games.value.filter(g => !g.is_wishlist))
  const wishlist = computed<Game[]>(() => games.value.filter(g => !!g.is_wishlist))

  const platformMap = computed<Record<number, Platform>>(() => {
    const map: Record<number, Platform> = {}
    for (const p of platforms.value) map[p.id] = p
    return map
  })

  // ── Actions ────────────────────────────────────────────────

  /** Load all data – skips if already cached, unless forced. */
  async function load(force = false): Promise<void> {
    if (loaded.value && !force) return
    loading.value = true
    error.value = null
    try {
      const [gRes, pRes] = await Promise.all([
        gamesApi.list(),
        platformsApi.list()
      ])
      games.value = Array.isArray(gRes.data) ? (gRes.data as Game[]) : []
      platforms.value = Array.isArray(pRes.data) ? (pRes.data as Platform[]) : []
      loaded.value = true
    } catch (e: unknown) {
      error.value = e
      console.error('[GameStore] Failed to load data:', e)
    } finally {
      loading.value = false
    }
  }

  /** Force a full refresh from the server (after add / delete / edit). */
  function refresh(): Promise<void> {
    return load(true)
  }

  /** Optimistically update a single game in the cache after an edit. */
  function updateGame(updatedGame: Partial<Game> & { id: number }): void {
    const idx = games.value.findIndex(g => g.id === updatedGame.id)
    if (idx !== -1) {
      games.value[idx] = { ...games.value[idx], ...updatedGame }
    }
  }

  /** Remove a single game from the cache after deletion. */
  function removeGame(id: number): void {
    games.value = games.value.filter(g => g.id !== id)
  }

  /** Add a newly created game to the cache. */
  function addGame(game: Game): void {
    games.value.push(game)
  }

  return {
    // state
    games, platforms, loading, loaded, error,
    // getters
    collection, wishlist, platformMap,
    // actions
    load, refresh, updateGame, removeGame, addGame
  }
})
