import { useUiStore } from '@/stores/uiStore';
export function useFactory() { const { activeFactoryId, setActiveFactory } = useUiStore(); return { factoryId: activeFactoryId, setFactoryId: setActiveFactory }; }
