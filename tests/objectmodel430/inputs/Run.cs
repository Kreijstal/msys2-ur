extern alias candidate;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using System.Resources;
using O=candidate::System.Collections.ObjectModel;
using S=candidate::System.Collections.Specialized;
using C=candidate::System.ComponentModel;
using ICommand=candidate::System.Windows.Input.ICommand;

sealed class Collection : O.ObservableCollection<int>
{
    internal IDisposable Block() => BlockReentrancy();
    internal void Check() => CheckReentrancy();
}
sealed class Item
{
    internal string Key;
    internal Item(string key) { Key=key; }
}
sealed class Keys : O.KeyedCollection<string,Item>
{
    internal Keys(int threshold) : base(StringComparer.OrdinalIgnoreCase,threshold) { }
    protected override string GetKeyForItem(Item item) => item.Key;
    internal void Change(Item item,string key) { ChangeItemKey(item,key);item.Key=key; }
    internal bool HasDictionary => Dictionary!=null;
}
sealed class Command : ICommand
{
    public event EventHandler? CanExecuteChanged;
    internal object? Last;
    public bool CanExecute(object parameter) => parameter!=null;
    public void Execute(object parameter) { Last=parameter;CanExecuteChanged?.Invoke(this,EventArgs.Empty); }
}
static class Program
{
    static int checks;
    static void Require(bool condition,string message) { checks++;if(!condition)throw new Exception(message); }
    static void Throws<T>(Action action,string message) where T:Exception
    {
        try { action(); } catch(T) { checks++;return; }
        throw new Exception("Expected "+typeof(T).Name+": "+message);
    }
    static void Main()
    {
        var assembly=typeof(O.ObservableCollection<>).Assembly;
        string path=assembly.Location.Replace('\\','/');
        Require(path.EndsWith("/System.ObjectModel.dll")&&!path.Contains("/shared/"),"Execute the source candidate");
        Require(!assembly.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),"Executable candidate");
        var version=assembly.GetName().Version!;
        Require(version==new Version(4,0,10,0)||version==new Version(4,0,13,0),"Original profile identity");
        var list=new O.ObservableCollection<int>();
        var order=new List<string>();
        S.NotifyCollectionChangedEventArgs? change=null;
        ((C.INotifyPropertyChanged)list).PropertyChanged+=(sender,args)=>{Require(ReferenceEquals(sender,list),"Property sender");order.Add(args.PropertyName!);};
        list.CollectionChanged+=(sender,args)=>{Require(ReferenceEquals(sender,list),"Collection sender");order.Add(args.Action.ToString());change=args;};
        list.Add(11);
        Require(order.SequenceEqual(new[]{"Count","Item[]","Add"}),"Add notification order");
        Require(change!.NewStartingIndex==0&&(int)change.NewItems![0]! ==11&&change.OldItems==null,"Add payload");
        order.Clear();list[0]=22;
        Require(order.SequenceEqual(new[]{"Item[]","Replace"})&&change!.OldStartingIndex==0&&(int)change.OldItems![0]! == 11&&(int)change.NewItems![0]! == 22,"Replace order and payload");
        list.Add(33);order.Clear();list.Move(0,1);
        Require(order.SequenceEqual(new[]{"Item[]","Move"})&&change!.OldStartingIndex==0&&change.NewStartingIndex==1&&(int)change.NewItems![0]! == 22,"Move payload");
        order.Clear();list.RemoveAt(0);
        Require(order.SequenceEqual(new[]{"Count","Item[]","Remove"})&&change!.OldStartingIndex==0&&(int)change.OldItems![0]! == 33,"Remove payload");
        order.Clear();list.Clear();
        Require(order.SequenceEqual(new[]{"Count","Item[]","Reset"})&&change!.NewItems==null&&change.OldItems==null,"Reset payload");
        Throws<ArgumentOutOfRangeException>(()=>list.Move(-1,0),"Invalid move");
        Throws<ArgumentNullException>(()=>new O.ObservableCollection<int>((IEnumerable<int>)null!),"Null constructor");
        var original=new List<int>{1,2,3};var copy=new O.ObservableCollection<int>(original);original.Clear();
        Require(copy.SequenceEqual(new[]{1,2,3}),"Constructor makes independent copy");
        var readOnly=new O.ReadOnlyObservableCollection<int>(copy);int collectionEvents=0,propertyEvents=0;
        ((S.INotifyCollectionChanged)readOnly).CollectionChanged+=(sender,args)=>{Require(ReferenceEquals(sender,readOnly),"Read-only collection sender");collectionEvents++;};
        ((C.INotifyPropertyChanged)readOnly).PropertyChanged+=(sender,args)=>{Require(ReferenceEquals(sender,readOnly),"Read-only property sender");propertyEvents++;};
        copy.Add(4);Require(readOnly.Count==4&&readOnly[3]==4&&collectionEvents==1&&propertyEvents==2,"Read-only view forwards events");
        Throws<NotSupportedException>(()=>((IList<int>)readOnly).Add(8),"Read-only mutation");
        var reentrant=new Collection();int calls=0;
        reentrant.CollectionChanged+=(sender,args)=>{calls++;if(reentrant.Count==1)reentrant.Add(2);};
        reentrant.Add(1);Require(calls==2&&reentrant.Count==2,"Single subscriber reentrancy permitted");
        reentrant.CollectionChanged+=(sender,args)=>{};
        using(reentrant.Block()) { Throws<InvalidOperationException>(()=>reentrant.Add(3),"Multiple subscribers reject reentrancy"); }
        reentrant.Check();reentrant.Add(3);Require(reentrant.Count==3,"Reentrancy scope released");
        var dictionary=new Dictionary<string,int>{{"one",1},{"two",2}};var ro=new O.ReadOnlyDictionary<string,int>(dictionary);
        Require(ro["one"]==1&&ro.Keys.Count==2&&ro.Values.Count==2&&ro.ContainsKey("two"),"Dictionary read surface");
        dictionary["three"]=3;Require(ro.Count==3&&ro["three"]==3,"Dictionary view tracks backing store");
        Throws<NotSupportedException>(()=>((IDictionary<string,int>)ro).Add("four",4),"Generic dictionary add");
        Throws<NotSupportedException>(()=>((IDictionary)ro)["one"]=4,"Non-generic dictionary set");
        Throws<NotSupportedException>(()=>((ICollection<string>)ro.Keys).Clear(),"Key view clear");
        Throws<NotSupportedException>(()=>((ICollection<int>)ro.Values).Add(4),"Value view add");
        var entries=new DictionaryEntry[3];((ICollection)ro).CopyTo(entries,0);Require(entries.Length==3&&entries.All(e=>dictionary[(string)e.Key]==(int)e.Value!),"DictionaryEntry CopyTo");
        var keys=new string[4];ro.Keys.CopyTo(keys,1);Require(keys.Skip(1).ToHashSet().SetEquals(dictionary.Keys),"Key CopyTo");
        Throws<ArgumentException>(()=>((ICollection)ro).CopyTo(new int[3],0),"CopyTo incompatible array");
        foreach(int threshold in new[]{-1,0,2})
        {
            var keyed=new Keys(threshold);var a=new Item("Alpha");keyed.Add(a);keyed.Add(new Item("Beta"));keyed.Add(new Item("Gamma"));
            Require(keyed.Contains("ALPHA")&&ReferenceEquals(keyed["alpha"],a),"Key comparer");
            Require(keyed.HasDictionary==(threshold!=-1),"Dictionary creation threshold");
            Throws<ArgumentException>(()=>keyed.Add(new Item("alpha")),"Duplicate key");
            keyed.Change(a,"Delta");Require(!keyed.Contains("alpha")&&keyed.Contains("DELTA"),"Changed item key updates lookup");
            Throws<ArgumentException>(()=>keyed.Change(a,"beta"),"Duplicate changed key");
            Require(keyed.Remove("delta")&&!keyed.Contains("delta")&&keyed.Count==2,"Remove by key");
            keyed.Clear();Require(keyed.Count==0&&!keyed.Contains("beta"),"Clear keyed collection");
        }
        Throws<ArgumentOutOfRangeException>(()=>new Keys(-2),"Invalid dictionary threshold");
        Require(new C.PropertyChangedEventArgs(null).PropertyName==null&&new C.PropertyChangingEventArgs("x").PropertyName=="x"&&new C.DataErrorsChangedEventArgs("y").PropertyName=="y","Component event arguments");
        var command=new Command();int notifications=0;command.CanExecuteChanged+=(sender,args)=>notifications++;object token=new object();
        Require(command.CanExecute(token)&&!command.CanExecute(null!),"ICommand CanExecute");command.Execute(token);
        Require(ReferenceEquals(command.Last,token)&&notifications==1,"ICommand Execute and event");
        var manager=new ResourceManager("FxResources.System.ObjectModel.SR",assembly);
        Require(!string.IsNullOrEmpty(manager.GetString("ObservableCollectionReentrancyNotAllowed",CultureInfo.InvariantCulture)),"Original resource lookup");
        var reset=new S.NotifyCollectionChangedEventArgs(S.NotifyCollectionChangedAction.Reset);
        Require(reset.Action==S.NotifyCollectionChangedAction.Reset&&reset.NewItems==null&&reset.NewStartingIndex==-1,"Reset constructor");
        Throws<ArgumentException>(()=>new S.NotifyCollectionChangedEventArgs(S.NotifyCollectionChangedAction.Add),"Invalid action constructor");
        Console.WriteLine("PASS source ObjectModel "+version+": "+checks+" event, reentrancy, dictionary, keyed collection, command, resource and exception checks");
    }
}
