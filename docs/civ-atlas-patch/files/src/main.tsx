// 所有样式最先放进来,先后见 ui/styles.ts(宽屏、手机的布局在最后,盖过各处的默认样式)
import './ui/styles';
import { createRoot } from 'react-dom/client';
import { scrubSecrets } from './ai/settings';
import { setDiagScrubber } from './diag/log';
import { installDiagWatch } from './diag/watch';
import { Boot, bootHelper } from './ui/Boot';
import { galleryHelperMode } from './ui/homeStart';
import { ErrorBoundary } from './ui/ErrorBoundary';

if (galleryHelperMode()) {
  // 帮手模式(作品墙的后台在看不见的框里打开网站画封面、列名字):不出界面、不记问题记录(不往浏览器里存东西)
  bootHelper();
} else {
  // 问题记录:最先接上,启动时出的错也记得到
  setDiagScrubber(scrubSecrets);
  installDiagWatch();

  // 先出首页、主程序在后台下载;不是首页的直接下载主程序(Boot.tsx)
  createRoot(document.getElementById('root')!).render(<ErrorBoundary><Boot /></ErrorBoundary>);
}
