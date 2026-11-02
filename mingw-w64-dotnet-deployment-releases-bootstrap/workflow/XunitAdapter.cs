// Minimal execution adapter for the four assertion APIs used by unchanged ReleaseVersionTests.
using System;
using System.Collections.Generic;
namespace Xunit
{
    [AttributeUsage(AttributeTargets.Method)]public sealed class FactAttribute:Attribute{}
    [AttributeUsage(AttributeTargets.Method)]public sealed class TheoryAttribute:Attribute{}
    [AttributeUsage(AttributeTargets.Method,AllowMultiple=true)]public sealed class InlineDataAttribute:Attribute{public object[] Data{get;}public InlineDataAttribute(params object[] data){Data=data;}}
    public static class Assert
    {
        public static void True(bool value){if(!value)throw new Exception("upstream Assert.True failed");}
        public static void Equal<T>(T expected,T actual){if(!EqualityComparer<T>.Default.Equals(expected,actual))throw new Exception("upstream Assert.Equal: expected="+expected+",actual="+actual);}
        public static void NotEqual<T>(T expected,T actual){if(EqualityComparer<T>.Default.Equals(expected,actual))throw new Exception("upstream Assert.NotEqual failed");}
        public static Exception Throws(Type expected,Action action){try{action();}catch(Exception e){if(e.GetType()==expected)return e;throw new Exception("upstream Assert.Throws expected="+expected+",actual="+e.GetType(),e);}throw new Exception("upstream Assert.Throws: no exception");}
        public static T Throws<T>(Action action) where T:Exception=>(T)Throws(typeof(T),action);
    }
}
