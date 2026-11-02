using System;
using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.ComponentModel;
static class Probe
{
    static void Main()
    {
        var items=new ObservableCollection<int>();
        int events=0;
        items.CollectionChanged+=(sender,args)=>{if(args.Action==NotifyCollectionChangedAction.Add)events++;};
        ((INotifyPropertyChanged)items).PropertyChanged+=(sender,args)=>{};
        items.Add(42);
        var view=new ReadOnlyObservableCollection<int>(items);
        if(view.Count!=1||view[0]!=42||events!=1)throw new Exception("Original typed contract");
    }
}
