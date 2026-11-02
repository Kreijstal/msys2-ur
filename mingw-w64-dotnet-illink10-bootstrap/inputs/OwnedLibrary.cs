using System;
public interface IValue<T>{T Read();}
public sealed class Value<T>:IValue<T> where T:class,new(){public T Read()=>new T();}
public class Base { public const int Number=42; public virtual string Text=>"π λ"; protected virtual int Kept()=>Number; }
public sealed class Derived:Base { public override string Text=>base.Text; }
internal sealed class UnusedInternal{public int Dead()=>-1;}
