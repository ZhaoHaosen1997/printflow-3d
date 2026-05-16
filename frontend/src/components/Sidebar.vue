<script setup>
import { ref, computed } from 'vue'
import { Palette, Layers, Package, Settings, ChevronDown, Paintbrush, ShoppingBag } from '@lucide/vue'
import { useRoute } from 'vue-router'
import { useTheme } from '../composables/useTheme'

const route = useRoute()
const { themes, currentTheme, setTheme } = useTheme()

const topItems = [
  { to: '/products', label: '商品管理', icon: Package },
  { to: '/orders', label: '订单管理', icon: ShoppingBag },
]

const sysGroup = {
  label: '系统管理',
  icon: Settings,
  items: [
    { to: '/colors', label: '配色管理', icon: Palette },
    { to: '/filaments', label: '耗材管理', icon: Layers },
  ],
}

const sysExpanded = ref(
  sysGroup.items.some(item => route.path.startsWith(item.to))
)

const sysActive = computed(() =>
  sysGroup.items.some(item => route.path.startsWith(item.to))
)

function toggleSys() {
  sysExpanded.value = !sysExpanded.value
}
</script>

<template>
  <aside class="w-60 flex-shrink-0 bg-dark-card border-r border-border-inner flex flex-col">
    <div class="p-5 border-b border-border-inner">
      <h1 class="text-xl font-serif text-gold-title tracking-wide">PrintFlow 3D</h1>
      <p class="text-xs text-gold-muted mt-1">v1.1.0</p>
    </div>
    <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
      <!-- Top-level items -->
      <router-link
        v-for="item in topItems"
        :key="item.to"
        :to="item.to"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors"
        :class="
          route.path.startsWith(item.to)
            ? 'bg-gold/10 text-gold border border-border-main/30'
            : 'text-gray-400 hover:text-gray-200 hover:bg-dark-input'
        "
      >
        <component :is="item.icon" class="w-4 h-4" />
        {{ item.label }}
      </router-link>

      <!-- System management group -->
      <div class="pt-3">
        <button
          class="flex items-center justify-between w-full px-3 py-2 rounded-lg text-sm transition-colors"
          :class="
            sysActive
              ? 'text-gold'
              : 'text-gray-500 hover:text-gray-300'
          "
          @click="toggleSys"
        >
          <div class="flex items-center gap-3">
            <component :is="sysGroup.icon" class="w-4 h-4" />
            {{ sysGroup.label }}
          </div>
          <ChevronDown
            class="w-4 h-4 transition-transform duration-200"
            :class="{ 'rotate-180': sysExpanded }"
          />
        </button>

        <div
          v-show="sysExpanded"
          class="mt-1 ml-2 space-y-1 border-l border-border-inner/50 pl-2"
        >
          <router-link
            v-for="item in sysGroup.items"
            :key="item.to"
            :to="item.to"
            class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors"
            :class="
              route.path.startsWith(item.to)
                ? 'bg-gold/10 text-gold border border-border-main/30'
                : 'text-gray-400 hover:text-gray-200 hover:bg-dark-input'
            "
          >
            <component :is="item.icon" class="w-4 h-4" />
            {{ item.label }}
          </router-link>

          <!-- Theme switcher -->
          <div class="px-3 py-2">
            <div class="flex items-center gap-2 text-xs text-gold-muted mb-2">
              <Paintbrush class="w-3.5 h-3.5" />
              切换主题
            </div>
            <div class="space-y-1">
              <button
                v-for="t in themes"
                :key="t.id"
                class="flex items-center gap-2 w-full px-2 py-1.5 rounded text-xs transition-colors"
                :class="
                  currentTheme === t.id
                    ? 'bg-gold/10 text-gold'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-dark-input'
                "
                @click="setTheme(t.id)"
              >
                <span class="flex gap-0.5">
                  <span
                    v-for="(c, i) in t.colors"
                    :key="i"
                    class="w-3 h-3 rounded-full border border-border-inner/30"
                    :style="{ backgroundColor: c }"
                  ></span>
                </span>
                {{ t.name }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  </aside>
</template>
