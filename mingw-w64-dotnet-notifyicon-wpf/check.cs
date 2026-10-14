using System;
using Hardcodet.Wpf.TaskbarNotification;
using System.Windows;
using System.Windows.Threading;
class Check {[STAThread] static void Main(){var icon=new TaskbarIcon {Visibility=Visibility.Collapsed,ToolTipText="Greenshot λ"};if(icon.IsDisposed||icon.ToolTipText!="Greenshot λ")throw new Exception("real WPF tray object/property state");icon.Dispose();icon.Dispose();if(!icon.IsDisposed)throw new Exception("tray resource cleanup");Dispatcher.CurrentDispatcher.InvokeShutdown();Console.WriteLine("PASS NotifyIcon real WPF construction, native message sink, properties and idempotent disposal");}}
