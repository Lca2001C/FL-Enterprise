import { useCallback, useRef } from 'react';
import { driver, type DriveStep, type Driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import type { AppTab } from '../apiTypes';
import {
  clearOwnerTourCompleted,
  clearOwnerTourBannerDismissed,
  getOwnerTourSteps,
  markOwnerTourCompleted,
  type OwnerTourStep,
} from './ownerTourSteps';
import { enhanceTourPopover } from './tourPopoverEnhancer';

function waitForElement(selector: string, timeoutMs = 5000): Promise<Element | null> {
  return new Promise((resolve) => {
    const existing = document.querySelector(selector);
    if (existing) {
      resolve(existing);
      return;
    }
    const started = Date.now();
    const timer = window.setInterval(() => {
      const el = document.querySelector(selector);
      if (el) {
        window.clearInterval(timer);
        resolve(el);
        return;
      }
      if (Date.now() - started >= timeoutMs) {
        window.clearInterval(timer);
        resolve(null);
      }
    }, 60);
  });
}

function stepSelector(step: OwnerTourStep): string | undefined {
  if (!step.tourId) return undefined;
  return `[data-tour="${step.tourId}"]`;
}

function toDriveStep(step: OwnerTourStep, index: number, total: number): DriveStep {
  const selector = stepSelector(step);
  return {
    element: selector,
    popover: {
      title: step.title,
      description: step.description,
      side: selector ? 'bottom' : 'over',
      align: 'center',
      showProgress: true,
      progressText: `${index + 1} de ${total}`,
    },
  };
}

type UseOwnerTourOptions = {
  role: string | null | undefined;
  setActiveTab: (tab: AppTab) => void;
  getActiveTab: () => AppTab;
};

export function useOwnerTour({ role, setActiveTab, getActiveTab }: UseOwnerTourOptions) {
  const driverRef = useRef<Driver | null>(null);
  const metaRef = useRef<OwnerTourStep[]>([]);
  const navigatingRef = useRef(false);

  const prepareStep = useCallback(
    async (meta: OwnerTourStep) => {
      if (meta.tab && getActiveTab() !== meta.tab) {
        setActiveTab(meta.tab);
        await new Promise((r) => window.setTimeout(r, 120));
      }
      const selector = stepSelector(meta);
      if (selector) {
        await waitForElement(selector);
      }
    },
    [getActiveTab, setActiveTab]
  );

  const destroyDriver = useCallback(() => {
    driverRef.current?.destroy();
    driverRef.current = null;
  }, []);

  const startTour = useCallback(async () => {
    if (navigatingRef.current) return;
    navigatingRef.current = true;
    destroyDriver();

    const metas = getOwnerTourSteps(role);
    metaRef.current = metas;
    if (metas.length === 0) {
      navigatingRef.current = false;
      return;
    }

    await prepareStep(metas[0]);

    const driveSteps = metas.map((m, i) => toDriveStep(m, i, metas.length));

    const driverObj = driver({
      steps: driveSteps,
      animate: true,
      allowClose: true,
      smoothScroll: true,
      overlayColor: '#020617',
      overlayOpacity: 0.78,
      stagePadding: 14,
      stageRadius: 16,
      popoverOffset: 16,
      showProgress: true,
      nextBtnText: 'Continuar',
      prevBtnText: 'Voltar',
      doneBtnText: 'Finalizar tour',
      popoverClass: 'motopay-tour-popover',
      onPopoverRender: (popover, { state }) => {
        enhanceTourPopover(popover, state, metaRef.current);
      },
      onHighlightStarted: (_element, _step, { driver: d, state }) => {
        const idx = state.activeIndex ?? 0;
        const meta = metaRef.current[idx];
        if (meta?.tourId) {
          void waitForElement(`[data-tour="${meta.tourId}"]`).then(() => d.refresh());
        }
      },
      onNextClick: (_element, _step, { state, driver: d }) => {
        const currentIdx = state.activeIndex ?? 0;
        if (currentIdx >= metaRef.current.length - 1) {
          d.destroy();
          return;
        }
        const nextMeta = metaRef.current[currentIdx + 1];
        void prepareStep(nextMeta).then(() => d.moveNext());
      },
      onPrevClick: (_element, _step, { state, driver: d }) => {
        const prevIdx = (state.activeIndex ?? 0) - 1;
        if (prevIdx < 0) {
          d.movePrevious();
          return;
        }
        const prevMeta = metaRef.current[prevIdx];
        void prepareStep(prevMeta).then(() => d.movePrevious());
      },
      onDestroyed: () => {
        driverRef.current = null;
        navigatingRef.current = false;
        markOwnerTourCompleted();
      },
    });

    driverRef.current = driverObj;
    driverObj.drive();
    navigatingRef.current = false;
  }, [destroyDriver, prepareStep, role]);

  const resetTour = useCallback(() => {
    clearOwnerTourCompleted();
    clearOwnerTourBannerDismissed();
    setActiveTab('dashboard');
    void startTour();
  }, [setActiveTab, startTour]);

  return { startTour, resetTour, destroyDriver };
}
